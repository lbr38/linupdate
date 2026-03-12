# coding: utf-8

# https://github.com/excid3/python-apt/blob/master/doc/examples/inst.py

# Import libraries
import re
import time
from pathlib import Path
from tabulate import tabulate
from colorama import Fore, Style

# Import classes
from src.controllers.System import System
from src.controllers.App.Config import Config
from src.controllers.Exit import Exit
from src.controllers.App.Utils import Utils
from src.controllers.Status import update_status, save_status, restore_status

class Package:
    def __init__(self):
        self.systemController    = System()
        self.appConfigController = Config()
        self.exitController      = Exit()

        # Locks
        self.cache_clear_lock = '/tmp/linupdate.clear-cache.lock'
        self.available_packages_lock = '/tmp/linupdate.available-packages.lock'
        self.installed_packages_lock = '/tmp/linupdate.installed-packages.lock'
        self.update_running_lock = '/tmp/linupdate.update-running.lock'

        # Import libraries depending on the OS family

        # If Debian, import apt
        if (self.systemController.get_os_family() == 'Debian'):
            from src.controllers.Package.Apt import Apt
            self.myPackageManagerController = Apt()

        # If Redhat, import yum
        if (self.systemController.get_os_family() == 'Redhat'):
            from src.controllers.Package.Dnf import Dnf
            self.myPackageManagerController = Dnf()

    #-----------------------------------------------------------------------------------------------
    #
    #   Check for package exclusions
    #
    #-----------------------------------------------------------------------------------------------
    def exclude(self, ignore_exclusions):
        try:
            # Retrieve the list of packages to exclude from the config file
            configuration = self.appConfigController.get_conf()
            excludeAlways = configuration['update']['packages']['exclude']['always']
            excludeOnMajorUpdate = configuration['update']['packages']['exclude']['on_major_update']

            # Loop through the list of packages to update
            for package in self.packagesToUpdateList:
                install = True
                install_decision_message = ''

                # Ignore package if it is already marked as not to install
                if 'install' in package and not package['install']:
                    continue

                # Check for exclusions and exclude packages only if the ignore_exclusions parameter is False
                if not ignore_exclusions:
                    # If the package is in the list of packages to exclude (on major update), check if the available version is a major update
                    if excludeOnMajorUpdate:
                        # There can be regex in the excludeOnMajorUpdate list (e.g. apache.*), so we need to convert it to a regex pattern
                        # https://www.geeksforgeeks.org/python-check-if-string-matches-regex-list/
                        regex = '(?:% s)' % '|'.join(excludeOnMajorUpdate)

                        # Check if the package name matches the regex pattern
                        if re.match(regex, package['name']):
                            # Retrieve the first digit of the current and available versions
                            # If the first digit is different then it is a major update, exclude the package
                            if package['current_version'].split('.')[0] != package['target_version'].split('.')[0]:
                                self.myPackageManagerController.exclude(package['name'])
                                install = False
                                install_decision_message = '✕ (excluded)'

                    # If the package is in the list of packages to exclude (always), exclude it
                    if excludeAlways:
                        # There can be regex in the excludeAlways list (e.g. apache.*), so we need to convert it to a regex pattern
                        # https://www.geeksforgeeks.org/python-check-if-string-matches-regex-list/
                        regex = '(?:% s)' % '|'.join(excludeAlways)

                        # Check if the package name matches the regex pattern
                        if re.match(regex, package['name']):
                            self.myPackageManagerController.exclude(package['name'])
                            install = False
                            install_decision_message = '✕ (excluded)'

                # Edit self.packagesToUpdateList and add excluded key to the package
                self.packagesToUpdateList[self.packagesToUpdateList.index(package)]['install'] = install
                self.packagesToUpdateList[self.packagesToUpdateList.index(package)]['install_decision_message'] = install_decision_message

            del configuration, excludeAlways, excludeOnMajorUpdate
        except Exception as e:
            raise Exception('error while excluding packages: ' + str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   Remove all package exclusions
    #
    #-----------------------------------------------------------------------------------------------
    def remove_all_exclusions(self):
        try:
            # Remove all exclusions
            self.myPackageManagerController.remove_all_exclusions()
        except Exception as e:
            raise Exception('could not remove all package exclusions: ' + str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   Get installed packages
    #
    #-----------------------------------------------------------------------------------------------
    def get_installed_packages(self):
        try:
            update_status("Getting installed packages")

            # Create a lock file to indicate that the installed packages are being retrieved, to prevent other processes to access the cache while it is being updated
            try:
                if not Path(self.installed_packages_lock).is_file():
                    Path(self.installed_packages_lock).touch()
            except Exception as e:
                raise Exception('could not create installed packages lock file: ' + str(e))

            # Wait for the cache to be cleared if it is being cleared
            self.wait_for_cache_clear_lock()

            # Wait for update to finish if it is running
            self.wait_for_update_running_lock()

            # Get a list of installed packages
            return self.myPackageManagerController.get_installed_packages()

        except Exception as e:
            raise Exception('error while getting installed packages: ' + str(e))
        finally:
            # Remove the lock file
            if Path(self.installed_packages_lock).is_file():
                Path(self.installed_packages_lock).unlink()


    #-----------------------------------------------------------------------------------------------
    #
    #   Get available packages
    #
    #-----------------------------------------------------------------------------------------------
    def get_available_packages(self, dist_upgrade: bool = False):
        try:
            update_status('Getting available packages')

            # Create a lock file to indicate that the available packages are being retrieved, to prevent other processes to access the cache while it is being updated
            try:
                if not Path(self.available_packages_lock).is_file():
                    Path(self.available_packages_lock).touch()
            except Exception as e:
                raise Exception('could not create available packages lock file: ' + str(e))

            # Wait for the cache to be cleared if it is being cleared
            self.wait_for_cache_clear_lock()

            # Wait for update to finish if it is running
            self.wait_for_update_running_lock()

            # Get a list of available packages
            return self.myPackageManagerController.get_available_packages(dist_upgrade)

        except Exception as e:
            raise Exception('error while retrieving available packages: ' + str(e))
        finally:
            # Remove the lock file
            if Path(self.available_packages_lock).is_file():
                Path(self.available_packages_lock).unlink()


    #-----------------------------------------------------------------------------------------------
    #
    #   Update package cache
    #
    #-----------------------------------------------------------------------------------------------
    def update_cache(self):
        try:
            update_status('Updating cache')

            # Do not clear while update is running
            self.wait_for_update_running_lock()

            # Do not clear while another process is getting available packages
            self.wait_for_available_packages_lock()

            # Do not clear while another process is getting installed packages
            self.wait_for_installed_packages_lock()

            # Do not clear while another process is clearing the cache
            self.wait_for_cache_clear_lock()

            # Update cache
            self.myPackageManagerController.update_cache()

        except Exception as e:
            raise Exception('error while updating package cache: ' + str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   Clear package cache
    #
    #-----------------------------------------------------------------------------------------------
    def clear_cache(self):
        try:
            update_status('Clearing cache')

            # Do not clear while update is running
            self.wait_for_update_running_lock()

            # Do not clear while another process is getting available packages
            self.wait_for_available_packages_lock()

            # Do not clear while another process is getting installed packages
            self.wait_for_installed_packages_lock()

            # Do not clear while another process is clearing the cache
            self.wait_for_cache_clear_lock()

            # Create a lock file to indicate that the cache is being cleared, to prevent other processes to access the cache while it is being cleared
            try:
                if not Path(self.cache_clear_lock).is_file():
                    Path(self.cache_clear_lock).touch()
            except Exception as e:
                raise Exception('could not create cache clear lock file: ' + str(e))

            self.myPackageManagerController.clear_cache()
        except Exception as e:
            raise Exception('error while clearing package cache: ' + str(e))
        finally:
            # Remove the lock file
            if Path(self.cache_clear_lock).is_file():
                Path(self.cache_clear_lock).unlink()


    #-----------------------------------------------------------------------------------------------
    #
    #   Update packages
    #   This can be a list of specific packages or all packages
    #
    #-----------------------------------------------------------------------------------------------
    def update(self,
        packages_list: list = [],
        assume_yes: bool = False,
        ignore_exclusions: bool = False,
        check_updates: bool = False,
        dist_upgrade: bool = False,
        keep_oldconf: bool = True,
        clear_cache: bool = False,
        dry_run: bool = False):
        
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
            configuration = self.appConfigController.get_conf()

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

                # For each package in the list, if no current version or target version is provided, retrieve it
                # This is the case when the user uses the --update parameter
                for package in packages_list:
                    # Default values
                    current_version = ''
                    target_version = ''
                    repository = ''
                    install = True
                    install_decision_message = ''

                    # First, check if package is installed, if not skip it
                    is_installed = self.myPackageManagerController.is_installed(package['name'])

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
                            current_version = self.myPackageManagerController.get_current_version(package['name'])
                        if 'target_version' not in package:
                            target_version = self.myPackageManagerController.get_available_version(package['name'])

                        # If current version or target version have not been found, skip the package
                        if current_version == '' or target_version == '':
                            continue

                        # If current version and target version are the same, skip the package
                        if current_version == target_version:
                            continue

                        # Retrieve the source repository
                        if 'repository' not in package:
                            repository = self.myPackageManagerController.get_source_repository(package['name'], target_version)

                    # Add the package to the list
                    packages_list_temp.append({
                        'name': package['name'],
                        'current_version': current_version,
                        'target_version': target_version,
                        'repository': repository,
                        'install': install,
                        'install_decision_message': install_decision_message
                    })

                self.packagesToUpdateList = packages_list_temp

                del packages_list_temp

            # Otherwise, retrieve the list of all available packages
            else:
                # Retrieve available packages passing the dist_upgrade parameter
                # (which will, with apt, update the list of available packages including packages such as the kernel)
                self.packagesToUpdateList = self.get_available_packages(dist_upgrade)

            # Check for package exclusions
            self.exclude(ignore_exclusions)

            # Count packages to update and packages ignored
            self.packagesToUpdateCount = 0
            self.packagesIgnoredCount = 0

            for package in self.packagesToUpdateList:
                if 'install' in package and not package['install']:
                    self.packagesIgnoredCount += 1
                else:
                    self.packagesToUpdateCount += 1

            # Print the number of packages to update
            if dry_run:
                print('\n' + Fore.YELLOW + '(dry run) ' + Fore.GREEN + str(self.packagesToUpdateCount) + Style.RESET_ALL + ' packages would be updated, ' + Fore.YELLOW + str(self.packagesIgnoredCount) + Style.RESET_ALL + ' would be ignored \n')
            else:
                print('\n' + Fore.GREEN + str(self.packagesToUpdateCount) + Style.RESET_ALL + ' packages will be updated, ' + Fore.YELLOW + str(self.packagesIgnoredCount) + Style.RESET_ALL + ' will be ignored \n')

            # Convert the list of packages to a table
            table = []
            for package in self.packagesToUpdateList:
                installDecisionMessage = Fore.GREEN + '✔' + Style.RESET_ALL

                # If package is marked as not to install, then display a warning
                if 'install' in package and package['install'] != True:
                    # If there is an install_decision_message, use it
                    if 'install_decision_message' in package:
                        installDecisionMessage = Fore.YELLOW + package['install_decision_message'] + Style.RESET_ALL
                    else:
                        installDecisionMessage = Fore.YELLOW + '✕ (ignored)' + Style.RESET_ALL

                table.append(['', package['name'], package['current_version'], package['target_version'], package['repository'], installDecisionMessage])

                del installDecisionMessage

            # Print the table list of packages to update
            # Check prettytable for table with width control https://pypi.org/project/prettytable/
            print(tabulate(table, headers=["", "Package", "Current version", "Target version", "Repository", "Install decision"], tablefmt="simple"), end='\n\n')

            # If there are no packages to update
            if self.packagesToUpdateCount == 0:
                print(Fore.GREEN + ' No package updates \n' + Style.RESET_ALL)
                self.summary['update']['status'] = 'nothing-to-do'

                # Remove all exclusions before exiting
                self.remove_all_exclusions()

            # Quit if --check-updates param has been specified
            if check_updates == True:
                # Remove all exclusions before exiting
                self.remove_all_exclusions()
                self.exitController.clean_exit()

            # Quit here if there was no packages to update
            if self.packagesToUpdateCount == 0:
                return

            # Print again the number of packages if total count is > 50 to avoid the user to scroll up to see it
            if self.packagesToUpdateCount + self.packagesIgnoredCount > 50:
                if dry_run:
                    print('\n ' + Fore.YELLOW + '(dry run) ' + Fore.GREEN + str(self.packagesToUpdateCount) + Style.RESET_ALL + ' packages would be updated, ' + Fore.YELLOW + str(self.packagesIgnoredCount) + Style.RESET_ALL + ' would be ignored \n')
                else:
                    print('\n ' + Fore.GREEN + str(self.packagesToUpdateCount) + Style.RESET_ALL + ' packages will be updated, ' + Fore.YELLOW + str(self.packagesIgnoredCount) + Style.RESET_ALL + ' will be ignored \n')

            # If --assume-yes param has not been specified, then ask for confirmation before installing the printed packages update list
            if not assume_yes:
                confirmMsg = 'Update now'

                if dry_run:
                    confirmMsg += ' (dry run)'

                update_status('Waiting for user confirmation...')

                # Ask for user confirmation and quit if the answer is not 'y'
                if not Utils().confirm(confirmMsg):
                    print(Fore.YELLOW + 'Cancelled' + Style.RESET_ALL)
                    # Remove all exclusions before exiting
                    self.remove_all_exclusions()
                    self.exitController.clean_exit()
                
            # If assume_yes, just print the message
            update_status(' ')

            # If 'linupdate' is in the list of packages to update, then add a temporary file in /tmp to
            # indicate that a service restart is needed. The service will be restarted by the linupdate service itself.
            # Important: this file must be created before the update process starts, so this is the right place to do it.
            for package in self.packagesToUpdateList:
                if package['name'] == 'linupdate':
                    if not Path(restart_file).is_file():
                        Path(restart_file).touch()

            # Create a temporary file in /tmp to indicate that the update process is running
            if not Path(self.update_running_lock).is_file():
                Path(self.update_running_lock).touch()

            # Execute the packages update
            self.myPackageManagerController.dist_upgrade = dist_upgrade
            self.myPackageManagerController.keep_oldconf = keep_oldconf
            self.myPackageManagerController.update(self.packagesToUpdateList, exit_on_package_update_error, dry_run)

            # Update the summary status
            self.summary['update']['status'] = 'done'

            del restart_file, configuration, packages_list, ignore_exclusions

        except Exception as e:
            print('\n' + Fore.RED + ' Packages update failed: ' + str(e) + Style.RESET_ALL)
            self.summary['update']['status'] = 'failed'

        finally:
            # Remove all exclusions
            self.remove_all_exclusions()

            # Remove the update running lock file
            if Path(self.update_running_lock).is_file():
                Path(self.update_running_lock).unlink()

        # Update the summary with the number of packages updated and failed
        if hasattr(self.myPackageManagerController, 'summary'):
            self.summary['update']['success']['count'] = self.myPackageManagerController.summary['update']['success']['count']
            self.summary['update']['failed']['count'] = self.myPackageManagerController.summary['update']['failed']['count']

            # Also retrieve the list of packages updated and failed, with their version and log
            self.summary['update']['success']['packages'] = self.myPackageManagerController.summary['update']['success']['packages']
            self.summary['update']['failed']['packages'] = self.myPackageManagerController.summary['update']['failed']['packages']

        # Print the number of packages updated and failed
        # If there was a failed package, print the number in red
        if self.summary['update']['failed']['count'] > 0:
            print('\n' + Fore.GREEN + str(self.summary['update']['success']['count']) + Style.RESET_ALL + ' packages updated, ' + Fore.RED + str(self.summary['update']['failed']['count']) + Style.RESET_ALL + ' packages failed' + Style.RESET_ALL)
        else:
            print('\n' + Fore.GREEN + str(self.summary['update']['success']['count']) + Style.RESET_ALL + ' packages updated, ' + str(self.summary['update']['failed']['count']) + ' packages failed' + Style.RESET_ALL)

        # If there was a failed package update and the package update error is critical (set to true), then raise an exception to exit
        if exit_on_package_update_error == True and (self.summary['update']['failed']['count'] > 0 or self.summary['update']['status'] == 'failed'):
            raise Exception('Critical error: package update failed')


    #-----------------------------------------------------------------------------------------------
    #
    #   Return history items (log file or history Ids) for a specific order
    #
    #-----------------------------------------------------------------------------------------------
    def get_history(self, order):
        return self.myPackageManagerController.get_history(order)


    #-----------------------------------------------------------------------------------------------
    #
    #   Parse history entries
    #
    #-----------------------------------------------------------------------------------------------
    def parse_history(self, entries, entries_limit):
        return self.myPackageManagerController.parse_history(entries, entries_limit)


    #-----------------------------------------------------------------------------------------------
    #
    #   Wait for a lock file to be released
    #
    #-----------------------------------------------------------------------------------------------
    def wait_for_lock(self, lock_file, timeout: int) -> None:
        start_time = time.time()

        while time.time() - start_time < timeout:
            locks_held = False

            if Path(lock_file).is_file():
                locks_held = True

            if not locks_held:
                return

            time.sleep(2)

        raise Exception('could not acquire lock ' + lock_file + ' within ' + str(timeout) + ' seconds')


    #-----------------------------------------------------------------------------------------------
    #
    #   Wait for update running lock to be released
    #   Default timeout is 60 seconds
    #
    #-----------------------------------------------------------------------------------------------
    def wait_for_update_running_lock(self, timeout: int = 60) -> None:
        # Save status message
        save_status()

        update_status('Another process is running an update, waiting for it to finish...')
        self.wait_for_lock(self.update_running_lock, timeout)

        # Restore status message
        restore_status()


    #-----------------------------------------------------------------------------------------------
    #
    #   Wait for available packages lock to be released
    #   Default timeout is 60 seconds
    #
    #-----------------------------------------------------------------------------------------------
    def wait_for_available_packages_lock(self, timeout: int = 60) -> None:
        # Save status message
        save_status()

        update_status('Waiting for available packages lock to be released...')
        self.wait_for_lock(self.available_packages_lock, timeout)

        # Restore status message
        restore_status()


    #-----------------------------------------------------------------------------------------------
    #
    #   Wait for installed packages lock to be released
    #   Default timeout is 60 seconds
    #
    #-----------------------------------------------------------------------------------------------
    def wait_for_installed_packages_lock(self, timeout: int = 60) -> None:
        # Save status message
        save_status()

        update_status('Waiting for installed packages lock to be released...')
        self.wait_for_lock(self.installed_packages_lock, timeout)

        # Restore status message
        restore_status()


    #-----------------------------------------------------------------------------------------------
    #
    #   Wait for cache clear lock to be released
    #   Default timeout is 60 seconds
    #
    #-----------------------------------------------------------------------------------------------
    def wait_for_cache_clear_lock(self, timeout: int = 60) -> None:
        # Save status message
        save_status()

        update_status('Waiting for cache clear lock to be released...')
        self.wait_for_lock(self.cache_clear_lock, timeout)

        # Restore status message
        restore_status()
