# coding: utf-8

# Import libraries
from colorama import Fore, Style
import socket

# Import classes
from src.controllers.System import System
from src.controllers.App.App import App
from src.controllers.App.Config import Config
from src.controllers.Module.Reposerver.Config import Config as ReposerverConfig
from src.controllers.Exit import Exit
from src.controllers.Package.Package import Package
from src.controllers.HttpRequest import HttpRequest

class Status:
    def __init__(self):
        self.systemController           = System()
        self.appController              = App()
        self.configController           = Config()
        self.reposerverConfigController = ReposerverConfig()
        self.httpRequestController      = HttpRequest()
        self.packageController          = Package()
        self.exitController             = Exit()


    #-----------------------------------------------------------------------------------------------
    #
    #   Send general status
    #
    #-----------------------------------------------------------------------------------------------
    def send_general_info(self):
        try:
            # Retrieve URL, ID and token
            url = self.reposerverConfigController.getUrl()
            id = self.reposerverConfigController.getId()
            token = self.reposerverConfigController.getToken()

            data = {
                'hostname': socket.getfqdn(),
                'os_family': self.systemController.get_os_family(),
                'os': self.systemController.get_os_name(),
                'os_version': self.systemController.get_os_version(),
                'type': self.systemController.get_virtualization(),
                'kernel': self.systemController.get_kernel(),
                'arch': self.systemController.get_arch(),
                'profile': self.configController.get_profile(),
                'env': self.configController.get_environment(),
                'agent_status': self.appController.get_agent_status(),
                'linupdate_version': self.appController.get_version(),
                'reboot_required': str(self.systemController.reboot_required()).lower() # Convert True/False to 'true'/'false'
            }

            print('\n  ▪ Sending general informations to ' + Fore.YELLOW + url + Style.RESET_ALL + ':')

        except Exception as e:
            raise Exception('could not build general status data: ' + str(e))

        try:
            self.httpRequestController.quiet = False
            self.httpRequestController.put(url + '/api/v2/host/status', id, token, data, 5, 10)
        except Exception as e:
            raise Exception('error while sending general status to reposerver: ' + str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   Send all packages status
    #
    #-----------------------------------------------------------------------------------------------
    def send_packages_info(self):
        try:
            # Send all status
            self.send_packages_history()
            self.sendAvailablePackagesStatus()
            self.sendInstalledPackagesStatus()
        except Exception as e:           
            raise Exception('error while sending packages status to reposerver: ' + str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   Send list of available packages
    #
    #-----------------------------------------------------------------------------------------------
    def sendAvailablePackagesStatus(self):
        # Retrieve URL, ID and token
        url = self.reposerverConfigController.getUrl()
        id = self.reposerverConfigController.getId()
        token = self.reposerverConfigController.getToken()

        available_packages = 'none'

        print('\n  ▪ Building available packages list...')

        try:
            # Retrieve available packages
            # Include package of dist upgrade => True
            packages = self.packageController.get_available_packages(True)

            if len(packages) > 0:
                available_packages = ''

                for package in packages:
                    name = package['name']
                    available_version = package['target_version']

                    # Ignore package if name is empty
                    if name == '':
                        continue

                    # Redhat only
                    if self.systemController.get_os_family() == 'Redhat':
                        # Remove epoch if it is equal to 0
                        if available_version.startswith('0:'):
                            available_version = available_version[2:]

                    # Add package name, its available version to the available_packages string
                    available_packages += name + '|' + available_version + ','

                # Remove last comma
                available_packages = available_packages[:-1]

            # Convert to JSON
            data = {
                'available_packages': available_packages
            }

        except Exception as e:
            # Raise an exception to be caught in the main function
            raise Exception('error while retrieving available packages: ' + str(e))

        # Send available packages to Reposerver
        print('  ▪ Sending available packages to ' + Fore.YELLOW + url + Style.RESET_ALL + ':')

        self.httpRequestController.quiet = False
        self.httpRequestController.put(url + '/api/v2/host/packages/available', id, token, data, 5, 10)


    #-----------------------------------------------------------------------------------------------
    #
    #   Send list of installed packages
    #
    #-----------------------------------------------------------------------------------------------
    def sendInstalledPackagesStatus(self):
        # Retrieve URL, ID and token
        url = self.reposerverConfigController.getUrl()
        id = self.reposerverConfigController.getId()
        token = self.reposerverConfigController.getToken()

        installed_packages = ''

        print('\n  ▪ Building installed packages list...')

        try:
            # Retrieve installed packages
            packages = self.packageController.get_installed_packages()

            if len(packages) > 0:
                for package in packages:
                    name = package['name']
                    version = package['version']

                    # Ignore package if name or version is empty
                    if name == '' or version == '':
                        continue

                    # Add package name, its available version to the installed_packages string
                    installed_packages += name + '|' + version + ','

                # Remove last comma
                installed_packages = installed_packages[:-1]

            # Convert to JSON
            data = {
                'installed_packages': installed_packages
            }

        except Exception as e:
            # Raise an exception to set status to 'error'
            raise Exception('error while retrieving installed packages: ' + str(e))
        
        # Send installed packages to Reposerver
        print('  ▪ Sending installed packages to ' + Fore.YELLOW + url + Style.RESET_ALL + ':')

        self.httpRequestController.quiet = False
        self.httpRequestController.put(url + '/api/v2/host/packages/installed', id, token, data, 5, 10)


    #-----------------------------------------------------------------------------------------------
    #
    #   Send packages history (installed, removed, upgraded, downgraded, etc.)
    #
    #-----------------------------------------------------------------------------------------------
    def send_packages_history(self, entries_limit: int = 999999):
        # Retrieve URL, ID and token
        url = self.reposerverConfigController.getUrl()
        id = self.reposerverConfigController.getId()
        token = self.reposerverConfigController.getToken()

        # History parsing will start from the oldest to the newest
        history_order = 'oldest'

        print('\n  ▪ Building packages history...')

        # If limit is set (not the default 999999), history parsing will start from the newest to the oldest
        if entries_limit != 999999:        
            history_order = 'newest'

        try:
            # Retrieve history Ids or files
            history_entries = self.packageController.get_history(history_order)
        except Exception as e:
            raise Exception('error while retrieving history: ' + str(e))

        # If there is no item (would be strange), exit
        if len(history_entries) == 0:
            print(' no history found')
            return

        # Parse history files / Ids
        try:
            events = {}
            events['events'] = self.packageController.parse_history(history_entries, entries_limit)

            # debug only: print pretty json
            # import json
            # r = json.dumps(events)
            # json_object = json.loads(r)
            # json_formatted_str = json.dumps(json_object, indent=2)
            # print(json_formatted_str)
        except Exception as e:
            raise Exception('could not parse packages history: ' + str(e))

        print('  ▪ Sending packages events to ' + Fore.YELLOW + url + Style.RESET_ALL + ':')

        self.httpRequestController.quiet = False
        self.httpRequestController.put(url + '/api/v2/host/packages/event', id, token, events, 5, 10)
