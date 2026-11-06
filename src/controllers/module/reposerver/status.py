# coding: utf-8

"""Host status and packages information sent to the reposerver."""

# Import libraries
import socket
from colorama import Fore, Style

# Import classes
from src.controllers.system import System
from src.controllers.app.app import App
from src.controllers.app.config import Config
from src.controllers.module.reposerver.config import Config as ReposerverConfig
from src.controllers.exit import Exit
from src.controllers.package.package import Package
from src.controllers.http_request import HttpRequest
from src.controllers.linupdate_exception import LinupdateException

class Status:
    """Send host and packages information to the reposerver."""
    def __init__(self):
        self.system_controller           = System()
        self.app_controller              = App()
        self.config_controller           = Config()
        self.reposerver_config_controller = ReposerverConfig()
        self.http_request_controller      = HttpRequest(self.reposerver_config_controller.get_verify_ssl())
        self.package_controller          = Package()
        self.exit_controller             = Exit()


    def send_general_info(self):
        """Send general status"""
        try:
            # Retrieve URL, ID and token
            url = self.reposerver_config_controller.get_url()
            auth_id = self.reposerver_config_controller.get_id()
            token = self.reposerver_config_controller.get_token()

            data = {
                'hostname': socket.getfqdn(),
                'os_family': self.system_controller.get_os_family(),
                'os': self.system_controller.get_os_name(),
                'os_version': self.system_controller.get_os_version(),
                'type': self.system_controller.get_virtualization(),
                'kernel': self.system_controller.get_kernel(),
                'arch': self.system_controller.get_arch(),
                'cpu': self.system_controller.get_cpu_info(),
                'ram': self.system_controller.get_memory_info(),
                'network': self.system_controller.get_network_info(),
                'profile': self.config_controller.get_profile(),
                'env': self.config_controller.get_environment(),
                'agent_status': self.app_controller.get_agent_status(),
                'agent_version': self.app_controller.get_version(),
                'reboot_required': str(self.system_controller.reboot_required()).lower(), # Convert True/False to 'true'/'false'
                'uptime': self.system_controller.get_uptime()
            }

            print('\n▪ Sending general informations to ' + Fore.YELLOW + url + Style.RESET_ALL + ':')

        except Exception as e:
            raise LinupdateException('could not build general status data: ' + str(e)) from e

        try:
            self.http_request_controller.quiet = False
            self.http_request_controller.put(url + '/api/v2/host/status', auth_id, token, data, 5, 10)
        except Exception as e:
            raise LinupdateException('error while sending general status to reposerver: ' + str(e)) from e

        del url, auth_id, token, data


    def send_packages_info(self):
        """Send all packages status"""
        try:
            # Concurrency with a running linupdate process is handled by the package lock
            self.package_controller.update_cache()

            # Send all status
            self.send_packages_history()
            self.send_available_packages_status()
            self.send_installed_packages_status()
        except Exception as e:
            raise LinupdateException('error while sending packages status to reposerver: ' + str(e)) from e


    def send_available_packages_status(self):
        """Send list of available packages"""
        packages_list = []

        # Retrieve URL, ID and token
        url = self.reposerver_config_controller.get_url()
        auth_id = self.reposerver_config_controller.get_id()
        token = self.reposerver_config_controller.get_token()

        print('\n▪ Building available packages list...')

        try:
            # Retrieve available packages
            # Include package of dist upgrade => True
            packages = self.package_controller.get_available_packages(True)

            if len(packages) > 0:
                for package in packages:
                    name = package['name']
                    version = package['target_version']
                    repository = package['repository']
                    security = str(package.get('security', False)).lower()

                    # Ignore package if name is empty
                    if name == '':
                        continue

                    # Redhat only
                    if self.system_controller.get_os_family() == 'Redhat':
                        # Remove epoch if it is equal to 0
                        if version.startswith('0:'):
                            version = version[2:]

                    # Add package name, version and repository to the available_packages list
                    packages_list.append({
                        'name': name,
                        'version': version,
                        'repository': repository,
                        'security': security
                    })

                    del name, version, repository, security

            # Convert to JSON
            data = {
                'available_packages': packages_list
            }

        except Exception as e:
            # Raise an exception to be caught in the main function
            raise LinupdateException('error while retrieving available packages: ' + str(e)) from e

        # Send available packages to Reposerver
        print('▪ Sending available packages to ' + Fore.YELLOW + url + Style.RESET_ALL + ':')

        self.http_request_controller.quiet = False
        self.http_request_controller.put(url + '/api/v2/host/packages/available', auth_id, token, data, 5, 10)

        del url, auth_id, token, packages, data, packages_list


    def send_installed_packages_status(self):
        """Send list of installed packages"""
        packages_list = []

        # Retrieve URL, ID and token
        url = self.reposerver_config_controller.get_url()
        auth_id = self.reposerver_config_controller.get_id()
        token = self.reposerver_config_controller.get_token()

        print('\n▪ Building installed packages list...')

        try:
            # Retrieve installed packages
            packages = self.package_controller.get_installed_packages()

            if len(packages) > 0:
                for package in packages:
                    # Ignore package if name or version is empty
                    if package['name'] == '' or package['version'] == '':
                        continue

                    packages_list.append({
                        'name': package['name'],
                        'version': package['version']
                    })

            # Convert to JSON
            data = {
                'installed_packages': packages_list
            }

        except Exception as e:
            # Raise an exception to set status to 'error'
            raise LinupdateException('error while retrieving installed packages: ' + str(e)) from e

        # Send installed packages to Reposerver
        print('▪ Sending installed packages to ' + Fore.YELLOW + url + Style.RESET_ALL + ':')

        self.http_request_controller.quiet = False
        self.http_request_controller.put(url + '/api/v2/host/packages/installed', auth_id, token, data, 5, 10)

        del url, auth_id, token, packages, data


    def send_packages_history(self, entries_limit: int = 999999):
        """Send packages history (installed, removed, upgraded, downgraded, etc.)"""
        # Retrieve URL, ID and token
        url = self.reposerver_config_controller.get_url()
        auth_id = self.reposerver_config_controller.get_id()
        token = self.reposerver_config_controller.get_token()

        # History parsing will start from the oldest to the newest
        history_order = 'oldest'

        print('\n▪ Building packages history...')

        # If limit is set (not the default 999999), history parsing will start from the newest to the oldest
        if entries_limit != 999999:
            history_order = 'newest'

        try:
            # Retrieve history Ids or files
            history_entries = self.package_controller.get_history(history_order)
        except Exception as e:
            raise LinupdateException('error while retrieving history: ' + str(e)) from e

        # If there is no item (would be strange), exit
        if len(history_entries) == 0:
            print(' no history found')
            return

        # Parse history files / Ids
        try:
            events = {}
            events['events'] = self.package_controller.parse_history(history_entries, entries_limit)

            # debug only: print pretty json
            # import json
            # r = json.dumps(events)
            # json_object = json.loads(r)
            # json_formatted_str = json.dumps(json_object, indent=2)
            # print(json_formatted_str)
        except Exception as e:
            raise LinupdateException('could not parse packages history: ' + str(e)) from e

        print('▪ Sending packages events to ' + Fore.YELLOW + url + Style.RESET_ALL + ':')

        self.http_request_controller.quiet = False
        self.http_request_controller.put(url + '/api/v2/host/packages/event', auth_id, token, events, 5, 10)

        del url, auth_id, token, history_order, history_entries, events
