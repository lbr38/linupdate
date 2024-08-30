# coding: utf-8

# https://github.com/excid3/python-apt/blob/master/doc/examples/inst.py

# Import libraries
import re
from tabulate import tabulate
from colorama import Fore, Style
from pathlib import Path

# Import classes
from src.controllers.System import System
from src.controllers.App.Config import Config
from src.controllers.Exit import Exit

class Package:
    def __init__(self):
        self.systemController    = System()
        self.appConfigController = Config()
        self.exitController      = Exit()

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
    def exclude(self, ignore_exclude):
        try:
            # Create a new empty list of packages to update
            packagesToUpdateList = []

            # Retrieve the list of packages to exclude from the config file
            configuration = self.appConfigController.get_conf()
            excludeAlways = configuration['update']['packages']['exclude']['always']
            excludeOnMajorUpdate = configuration['update']['packages']['exclude']['on_major_update']

            # Loop through the list of packages to update
            for package in self.packagesToUpdateList:
                excluded = False

                # Check for exclusions and exclude packages only if the ignore_exclude parameter is False
                if not ignore_exclude:
                    # If the package is in the list of packages to exclude (on major update), check if the available version is a major update
                    if excludeOnMajorUpdate:
                        # There can be regex in the excludeOnMajorUpdate list (e.g. apache.*), so we need to convert it to a regex pattern
                        # https://www.geeksforgeeks.org/python-check-if-string-matches-regex-list/
                        regex = '(?:% s)' % '|'.join(excludeOnMajorUpdate)

                        # Check if the package name matches the regex pattern
                        if re.match(regex, package['name']):
                            # Retrieve the first digit of the current and available versions
                            # If the first digit is different then it is a major update, exclude the package
                            if package['current_version'].split('.')[0] != package['available_version'].split('.')[0]:
                                self.myPackageManagerController.exclude(package['name'])
                                excluded = True

                    # If the package is in the list of packages to exclude (always), exclude it
                    if excludeAlways:
                        # There can be regex in the excludeAlways list (e.g. apache.*), so we need to convert it to a regex pattern
                        # https://www.geeksforgeeks.org/python-check-if-string-matches-regex-list/
                        regex = '(?:% s)' % '|'.join(excludeAlways)

                        # Check if the package name matches the regex pattern
                        if re.match(regex, package['name']): 
                            self.myPackageManagerController.exclude(package['name'])
                            excluded = True

                # Add the package to the list of packages to update
                packagesToUpdateList.append({
                    'name': package['name'],
                    'current_version': package['current_version'],
                    'available_version': package['available_version'],
                    'excluded': excluded
                })

            # Replace the list of packages to update with the new list
            self.packagesToUpdateList = packagesToUpdateList

            del configuration, excludeAlways, excludeOnMajorUpdate, packagesToUpdateList
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
            # Get a list of installed packages
            return self.myPackageManagerController.get_installed_packages()
        
        except Exception as e:
            raise Exception('error while getting installed packages: ' + str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   Get available packages
    #
    #-----------------------------------------------------------------------------------------------
    def get_available_packages(self, update_cache: bool = True, dist_upgrade: bool = False):
        try:
            # If cache update is enabled
            if update_cache:
                # First, clear package manager cache
                self.myPackageManagerController.clear_cache()
                self.myPackageManagerController.update_cache(dist_upgrade)

            # Get a list of available packages
            return self.myPackageManagerController.get_available_packages()

        except Exception as e:
            raise Exception('error while retrieving available packages: ' + str(e))
    

    #-----------------------------------------------------------------------------------------------
    #
    #   Update packages
    #
    #-----------------------------------------------------------------------------------------------
    def update(self, assume_yes: bool = False, ignore_exclude: bool = False, check_updates: bool = False, dist_upgrade: bool = False, keep_oldconf: bool = True):        
        restart_file = '/tmp/linupdate.restart-needed'

        # Package update summary
        self.summary = {
            'update': {
                'status': 'running',
                'success': {
                    'count': 0,
                    'packages': []
                },
                'failed': {
                    'count': 0,
                    'packages': []
                },
            }
        }

        try:
            # Retrieve configuration
            configuration = self.appConfigController.get_conf()

            # Retrieve the update method
            update_method = configuration['update']['method']

            # Retrieve the exit_on_package_update_error option
            exit_on_package_update_error = configuration['update']['exit_on_package_update_error']

            # Remove all exclusions before starting (could be some left from a previous run that failed)
            self.remove_all_exclusions()
    
            # Retrieve available packages,
            # passing False for the update_cache parameter (which will not update the list of available packages) => maybe change this in the future
            # passing the dist_upgrade parameter (which will, with apt, update the list of available packages including packages such as the kernel)
            self.packagesToUpdateList = self.get_available_packages(True, dist_upgrade)

            # Check for package exclusions
            self.exclude(ignore_exclude)

            # Count packages to update and packages excluded
            self.packagesToUpdateCount = 0
            self.packagesExcludedCount = 0

            for package in self.packagesToUpdateList:
                if 'excluded' in package and package['excluded']:
                    self.packagesExcludedCount += 1
                else:
                    self.packagesToUpdateCount += 1

            # Print the number of packages to update
            print('\n ' + Fore.GREEN + str(self.packagesToUpdateCount) + Style.RESET_ALL + ' packages will be updated, ' + Fore.YELLOW + str(self.packagesExcludedCount) + Style.RESET_ALL + ' will be excluded \n')

            # Convert the list of packages to a table
            table = []
            for package in self.packagesToUpdateList:
                # If package is excluded
                if 'excluded' in package and package['excluded']:
                    installOrExclude = Fore.YELLOW + '✕ (excluded)' + Style.RESET_ALL
                else:
                    installOrExclude = Fore.GREEN + '✔' + Style.RESET_ALL

                table.append(['', package['name'], package['current_version'], package['available_version'], installOrExclude])

            # Print the table list of packages to update
            # Check prettytable for table with width control https://pypi.org/project/prettytable/
            print(tabulate(table, headers=["", "Package", "Current version", "Available version", "Install decision"], tablefmt="simple"), end='\n\n')

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
                self.exitController.clean_exit(0, False)

            # Quit here if there was no packages to update
            if self.packagesToUpdateCount == 0:
                return

            # If --assume-yes param has not been specified, then ask for confirmation before installing the printed packages update list
            if not assume_yes:
                # Ask for confirmation
                print('\n ' + Fore.YELLOW + 'Update now [y/N]' + Style.RESET_ALL, end=' ')

                answer = input()

                # Quit if the answer is not 'y'
                if answer.lower() != 'y':
                    print(Fore.YELLOW + ' Cancelled' + Style.RESET_ALL)
                    # Remove all exclusions before exiting
                    self.remove_all_exclusions()
                    self.exitController.clean_exit(0, False)

            print('\n Updating packages...')

            # If 'linupdate' is in the list of packages to update, then add a temporary file in /tmp to
            # indicate that a service restart is needed. The service will be restarted by the linupdate service itself.
            # Important: this file must be created before the update process starts, so this is the right place to do it.
            for package in self.packagesToUpdateList:
                if package['name'] == 'linupdate':
                    if not Path(restart_file).is_file():
                        Path(restart_file).touch()

            # Execute the packages update
            self.myPackageManagerController.dist_upgrade = dist_upgrade
            self.myPackageManagerController.keep_oldconf = keep_oldconf
            self.myPackageManagerController.update(self.packagesToUpdateList, update_method, exit_on_package_update_error)

            # Update the summary status
            self.summary['update']['status'] = 'done'

        except Exception as e:
            print(Fore.RED + ' ✕ ' + Style.RESET_ALL + str(e))
            print('\n' + Fore.RED + ' Packages update failed ' + Style.RESET_ALL)
            self.summary['update']['status'] = 'failed'

        finally:
            # Remove all exclusions
            self.remove_all_exclusions()

        # If update method is 'one_by_one', it will be possible to print precise information about the number of packages updated and failed
        if update_method == 'one_by_one':
            # Update the summary with the number of packages updated and failed
            self.summary['update']['success']['count'] = self.myPackageManagerController.summary['update']['success']['count']
            self.summary['update']['failed']['count'] = self.myPackageManagerController.summary['update']['failed']['count']

            # Print the number of packages updated and failed
            # If there was a failed package, print the number in red
            if self.summary['update']['failed']['count'] > 0:
                print('\n ' + Fore.GREEN + str(self.summary['update']['success']['count']) + Style.RESET_ALL + ' packages updated, ' + Fore.RED + str(self.summary['update']['failed']['count']) + Style.RESET_ALL + ' packages failed' + Style.RESET_ALL)
            else:
                print('\n ' + Fore.GREEN + str(self.summary['update']['success']['count']) + Style.RESET_ALL + ' packages updated, ' + str(self.summary['update']['failed']['count']) + ' packages failed' + Style.RESET_ALL)

        # If update method is 'global', just print success or failure
        if update_method == 'global':
            # If there was a failed package, print the number in red
            if self.summary['update']['status'] == 'done':
                print('\n ' + Fore.GREEN + 'All packages updated' + Style.RESET_ALL)
            else:
                print('\n ' + Fore.RED + 'Some packages failed to update' + Style.RESET_ALL)

        # If there was a failed package update and the package update error is critical (set to true), then raise an exception to exit
        if exit_on_package_update_error == True and self.summary['update']['failed']['count'] > 0:
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
    #   Clear package manager cache
    #
    #-----------------------------------------------------------------------------------------------
    def clear_cache(self):
        self.myPackageManagerController.clear_cache()
