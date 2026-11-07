# coding: utf-8

"""Package updates orchestration, independent of the package manager."""

# https://github.com/excid3/python-apt/blob/master/doc/examples/inst.py

# Import libraries
import re
from pathlib import Path
from tabulate import tabulate
from colorama import Fore, Style

# Import classes
from src.controllers.system import System
from src.controllers.app.config import Config
from src.controllers.exit import Exit
from src.controllers.app.utils import Utils
from src.controllers.status import update_status
from src.controllers.lock import Lock
from src.controllers.linupdate_exception import LinupdateException

class Package:
    """Run package updates with the system package manager (apt or dnf)."""
    def __init__(self):
        self.system_controller    = System()
        self.app_config_controller = Config()
        self.exit_controller      = Exit()

        # Set by update()
        self.summary = None
        self.packages_to_update_list = []
        self.packages_to_update_count = 0
        self.packages_ignored_count = 0

        # Import libraries depending on the OS family

        # If Debian, import apt
        if self.system_controller.get_os_family() == 'Debian':
            from src.controllers.package.apt import Apt # pylint: disable=import-outside-toplevel
            self.my_package_manager_controller = Apt()

        # If Redhat, import yum
        if self.system_controller.get_os_family() == 'Redhat':
            from src.controllers.package.dnf import Dnf # pylint: disable=import-outside-toplevel
            self.my_package_manager_controller = Dnf()

    def exclude(self, ignore_exclusions):
        """Check for package exclusions"""
        try:
            # Retrieve the list of packages to exclude from the config file
            configuration = self.app_config_controller.get_conf()
            exclude_always = configuration['update']['packages']['exclude']['always']
            exclude_on_major_update = configuration['update']['packages']['exclude']['on_major_update']

            # Loop through the list of packages to update
            for package in self.packages_to_update_list:
                install = True
                install_decision_message = ''

                # Ignore package if it is already marked as not to install
                if 'install' in package and not package['install']:
                    continue

                # Check for exclusions and exclude packages only if the ignore_exclusions parameter is False
                if not ignore_exclusions:
                    # If the package is in the list of packages to exclude (on major update), check if the available version is a major update
                    if exclude_on_major_update:
                        # There can be regex in the excludeOnMajorUpdate list (e.g. apache.*), so we need to convert it to a regex pattern
                        # https://www.geeksforgeeks.org/python-check-if-string-matches-regex-list/
                        regex = f"(?:{'|'.join(exclude_on_major_update)})"

                        # Check if the package name matches the regex pattern
                        if re.match(regex, package['name']):
                            # Retrieve the first digit of the current and available versions
                            # If the first digit is different then it is a major update, exclude the package
                            if package['current_version'].split('.')[0] != package['target_version'].split('.')[0]:
                                self.my_package_manager_controller.exclude(package['name'])
                                install = False
                                install_decision_message = '✕ (excluded)'

                    # If the package is in the list of packages to exclude (always), exclude it
                    if exclude_always:
                        # There can be regex in the excludeAlways list (e.g. apache.*), so we need to convert it to a regex pattern
                        # https://www.geeksforgeeks.org/python-check-if-string-matches-regex-list/
                        regex = f"(?:{'|'.join(exclude_always)})"

                        # Check if the package name matches the regex pattern
                        if re.match(regex, package['name']):
                            self.my_package_manager_controller.exclude(package['name'])
                            install = False
                            install_decision_message = '✕ (excluded)'

                # Edit self.packagesToUpdateList and add excluded key to the package
                self.packages_to_update_list[self.packages_to_update_list.index(package)]['install'] = install
                self.packages_to_update_list[self.packages_to_update_list.index(package)]['install_decision_message'] = install_decision_message

            del configuration, exclude_always, exclude_on_major_update
        except Exception as e:
            raise LinupdateException('error while excluding packages: ' + str(e)) from e


    def remove_all_exclusions(self):
        """Remove all package exclusions"""
        try:
            # Remove all exclusions
            self.my_package_manager_controller.remove_all_exclusions()
        except Exception as e:
            raise LinupdateException('could not remove all package exclusions: ' + str(e)) from e


    def get_installed_packages(self):
        """Get installed packages"""
        try:
            update_status("Getting installed packages")

            with self.package_lock(shared=True):
                return self.my_package_manager_controller.get_installed_packages()

        except Exception as e:
            raise LinupdateException('error while getting installed packages: ' + str(e)) from e


    def get_available_packages(self, dist_upgrade: bool = False):
        """Get available packages"""
        try:
            update_status('Getting available packages')

            with self.package_lock(shared=True):
                return self.my_package_manager_controller.get_available_packages(dist_upgrade)

        except Exception as e:
            raise LinupdateException('error while retrieving available packages: ' + str(e)) from e


    def update_cache(self):
        """Update package cache"""
        try:
            update_status('Updating cache')

            with self.package_lock():
                self.my_package_manager_controller.update_cache()

        except Exception as e:
            raise LinupdateException('error while updating package cache: ' + str(e)) from e


    def clear_cache(self):
        """Clear package cache"""
        try:
            update_status('Clearing cache')

            with self.package_lock():
                self.my_package_manager_controller.clear_cache()
        except Exception as e:
            raise LinupdateException('error while clearing package cache: ' + str(e)) from e


    def update(self,
        packages_list: list = [],
        assume_yes: bool = False,
        ignore_exclusions: bool = False,
        check_updates: bool = False,
        dist_upgrade: bool = False,
        keep_oldconf: bool = True,
        clear_cache: bool = False,
        dry_run: bool = False):
        """Update packages

        This can be a list of specific packages or all packages
        """

        restart_file = '/tmp/linupdate.restart-needed'

        # Package update summary
        self.summary = {
            'update': {
                'status': 'running',
                'options': {
                    'dry_run': dry_run,
                },
                'success': {
                    'count': 0,
                    'packages': {}
                },
                'failed': {
                    'count': 0,
                    'packages': {}
                },
            }
        }

        try:
            update_status("Initialising updates...")

            # Retrieve configuration
            configuration = self.app_config_controller.get_conf()

            # Retrieve the exit_on_package_update_error option
            exit_on_package_update_error = configuration['update']['exit_on_package_update_error']

            # Remove all exclusions before starting (could be some left from a previous run that failed)
            self.remove_all_exclusions()

            # Clear cache
            if clear_cache:
                self.clear_cache()

            # Update cache
            self.update_cache()

            # If a list of packages to update has been provided, use it
            if len(packages_list) > 0:
                packages_list_temp = []

                # Retrieve the set of packages that have a security update available (single call)
                security_packages_set = self.my_package_manager_controller.get_security_packages_set()

                # For each package in the list, if no current version or target version is provided, retrieve it
                # This is the case when the user uses the --update parameter
                for package in packages_list:
                    # Default values
                    current_version = ''
                    target_version = ''
                    repository = ''
                    security = False
                    install = True
                    install_decision_message = ''

                    # First, check if package is installed, if not skip it
                    is_installed = self.my_package_manager_controller.is_installed(package['name'])

                    # If package is not installed, mark it as not to install
                    if not is_installed:
                        current_version = '-'
                        target_version = '-'
                        repository = '-'
                        install = False
                        install_decision_message = '✕ Package is not installed'

                    # If package is installed, retrieve the current and target versions
                    if is_installed:
                        if 'current_version' not in package:
                            current_version = self.my_package_manager_controller.get_current_version(package['name'])
                        if 'target_version' not in package:
                            target_version = self.my_package_manager_controller.get_available_version(package['name'])

                        # If current version or target version have not been found, skip the package
                        if current_version == '' or target_version == '':
                            continue

                        # If current version and target version are the same, skip the package
                        if current_version == target_version:
                            continue

                        # Retrieve the source repository
                        if 'repository' not in package:
                            repository = self.my_package_manager_controller.get_source_repository(package['name'], target_version)

                        # Detect if this is a security update
                        security = package['name'] in security_packages_set

                    # Add the package to the list
                    packages_list_temp.append({
                        'name': package['name'],
                        'current_version': current_version,
                        'target_version': target_version,
                        'repository': repository,
                        'security': security,
                        'install': install,
                        'install_decision_message': install_decision_message
                    })

                self.packages_to_update_list = packages_list_temp

                del packages_list_temp

            # Otherwise, retrieve the list of all available packages
            else:
                # Retrieve available packages passing the dist_upgrade parameter
                # (which will, with apt, update the list of available packages including packages such as the kernel)
                self.packages_to_update_list = self.get_available_packages(dist_upgrade)

            # Check for package exclusions
            self.exclude(ignore_exclusions)

            # Count packages to update and packages ignored
            self.packages_to_update_count = 0
            self.packages_ignored_count = 0

            for package in self.packages_to_update_list:
                if 'install' in package and not package['install']:
                    self.packages_ignored_count += 1
                else:
                    self.packages_to_update_count += 1

            # Print the number of packages to update
            if dry_run:
                print('\n' + Fore.YELLOW + '(dry run) ' + Fore.GREEN + str(self.packages_to_update_count) + Style.RESET_ALL + ' packages would be updated, ' + Fore.YELLOW + str(self.packages_ignored_count) + Style.RESET_ALL + ' would be ignored \n')
            else:
                print('\n' + Fore.GREEN + str(self.packages_to_update_count) + Style.RESET_ALL + ' packages will be updated, ' + Fore.YELLOW + str(self.packages_ignored_count) + Style.RESET_ALL + ' will be ignored \n')

            # Convert the list of packages to a table
            table = []
            for package in self.packages_to_update_list:
                # Build message and security indicator
                if 'install' in package and not package['install']:
                    # If there is an install_decision_message, use it
                    if 'install_decision_message' in package:
                        decision_message = package['install_decision_message']
                    else:
                        decision_message = '✕ (ignored)'
                else:
                    decision_message = '✔'

                security_text = 'yes' if package['security'] else 'no'

                # Build row
                row = ['', package['name'], package['current_version'], package['target_version'], package['repository'], security_text, decision_message]

                # If security update, color entire row in yellow
                if not package['install']:
                    row = [Fore.YELLOW + str(cell) + Style.RESET_ALL for cell in row]
                elif package['security']:
                    row = [Style.BRIGHT + str(cell) + Style.RESET_ALL for cell in row]
                else:
                    # For non-security updates, add color only to decision message
                    row[6] = Fore.GREEN + '✔' + Style.RESET_ALL if decision_message == '✔' else Fore.YELLOW + decision_message + Style.RESET_ALL

                table.append(row)

            # Print the table list of packages to update
            # Check prettytable for table with width control https://pypi.org/project/prettytable/
            print(tabulate(table, headers=["", "Package", "Current version", "Target version", "Repository", "Security fix", "Install decision"], tablefmt="simple"), end='\n\n')

            # If there are no packages to update
            if self.packages_to_update_count == 0:
                print(Fore.GREEN + ' No package updates \n' + Style.RESET_ALL)
                self.summary['update']['status'] = 'nothing-to-do'

                # Remove all exclusions before exiting
                self.remove_all_exclusions()

            # Quit if --check-updates param has been specified
            if check_updates:
                # Remove all exclusions before exiting
                self.remove_all_exclusions()
                self.exit_controller.clean_exit()

            # Quit here if there was no packages to update
            if self.packages_to_update_count == 0:
                return

            # Print again the number of packages if total count is > 50 to avoid the user to scroll up to see it
            if self.packages_to_update_count + self.packages_ignored_count > 50:
                if dry_run:
                    print('\n ' + Fore.YELLOW + '(dry run) ' + Fore.GREEN + str(self.packages_to_update_count) + Style.RESET_ALL + ' packages would be updated, ' + Fore.YELLOW + str(self.packages_ignored_count) + Style.RESET_ALL + ' would be ignored \n')
                else:
                    print('\n ' + Fore.GREEN + str(self.packages_to_update_count) + Style.RESET_ALL + ' packages will be updated, ' + Fore.YELLOW + str(self.packages_ignored_count) + Style.RESET_ALL + ' will be ignored \n')

            # If --assume-yes param has not been specified, then ask for confirmation before installing the printed packages update list
            if not assume_yes:
                confirm_msg = 'Update now'

                if dry_run:
                    confirm_msg += ' (dry run)'

                update_status('Waiting for user confirmation...')

                # Ask for user confirmation and quit if the answer is not 'y'
                if not Utils().confirm(confirm_msg):
                    print(Fore.YELLOW + 'Cancelled' + Style.RESET_ALL)
                    # Remove all exclusions before exiting
                    self.remove_all_exclusions()
                    self.exit_controller.clean_exit()

            # If assume_yes, just print the message
            update_status(' ')

            # If 'linupdate' is in the list of packages to update, then add a temporary file in /tmp to
            # indicate that a service restart is needed. The service will be restarted by the linupdate service itself.
            # Important: this file must be created before the update process starts, so this is the right place to do it.
            for package in self.packages_to_update_list:
                if package['name'] == 'linupdate':
                    if not Path(restart_file).is_file():
                        Path(restart_file).touch()

            # Execute the packages update
            with self.package_lock():
                self.my_package_manager_controller.dist_upgrade = dist_upgrade
                self.my_package_manager_controller.keep_oldconf = keep_oldconf
                self.my_package_manager_controller.update(self.packages_to_update_list, exit_on_package_update_error, dry_run)

            # Update the summary status
            self.summary['update']['status'] = 'done'

            del restart_file, configuration, packages_list, ignore_exclusions

        except Exception as e:
            print('\n' + Fore.RED + ' Packages update failed: ' + str(e) + Style.RESET_ALL)
            self.summary['update']['status'] = 'failed'

        finally:
            # Remove all exclusions
            self.remove_all_exclusions()

        # Update the summary with the number of packages updated and failed
        if self.my_package_manager_controller.summary is not None:
            self.summary['update']['success']['count'] = self.my_package_manager_controller.summary['update']['success']['count']
            self.summary['update']['failed']['count'] = self.my_package_manager_controller.summary['update']['failed']['count']

            # Also retrieve the list of packages updated and failed, with their version and log
            self.summary['update']['success']['packages'] = self.my_package_manager_controller.summary['update']['success']['packages']
            self.summary['update']['failed']['packages'] = self.my_package_manager_controller.summary['update']['failed']['packages']

        # Print the number of packages updated and failed
        # If there was a failed package, print the number in red
        if self.summary['update']['failed']['count'] > 0:
            print('\n' + Fore.GREEN + str(self.summary['update']['success']['count']) + Style.RESET_ALL + ' packages updated, ' + Fore.RED + str(self.summary['update']['failed']['count']) + Style.RESET_ALL + ' packages failed' + Style.RESET_ALL)
        else:
            print('\n' + Fore.GREEN + str(self.summary['update']['success']['count']) + Style.RESET_ALL + ' packages updated, ' + str(self.summary['update']['failed']['count']) + ' packages failed' + Style.RESET_ALL)

        # If there was a failed package update and the package update error is critical (set to true), then raise an exception to exit
        if exit_on_package_update_error and (self.summary['update']['failed']['count'] > 0 or self.summary['update']['status'] == 'failed'):
            raise LinupdateException('Critical error: package update failed')


    def get_history(self, order):
        """Return history items (log file or history Ids) for a specific order"""
        return self.my_package_manager_controller.get_history(order)


    def parse_history(self, entries, entries_limit):
        """Parse history entries"""
        return self.my_package_manager_controller.parse_history(entries, entries_limit)


    def package_lock(self, shared: bool = False) -> Lock:
        """Return the package manager lock

        Shared: reading packages (several readers allowed)
        Exclusive: modifying cache or installing packages
        """
        return Lock('package', shared, 3600, 'Another linupdate process is using the package manager, waiting for it to finish...')
