# coding: utf-8

# Import libraries
import subprocess
import re
from colorama import Fore, Style
from pathlib import Path

# Import classes
from src.controllers.App.Config import Config

class Service:
    #-----------------------------------------------------------------------------------------------
    #
    #   Restart services
    #
    #-----------------------------------------------------------------------------------------------
    def restart(self, update_summary: list, dry_run: bool = False):
        # Retrieve services to restart
        services = Config().get_service_to_restart()

        # Retrieve updated packages list from update summary
        updated_packages = update_summary['update']['success']['packages']
        updated_packages_count = update_summary['update']['success']['count']

        # Quit if no packages were updated
        if updated_packages_count == 0:
            return

        # Quit if systemctl is not installed (e.g. in docker container of linupdate's CI)
        if not Path('/usr/bin/systemctl').is_file():
            print('\n systemctl is not installed, skipping service restart')
            return

        print('\n Restarting services')

        # If no services to restart, skip
        if not services:
            print('  ▪ No services to restart')
            return

        # Restart services
        for service in services:
            # Check if there is a condition to restart the service (got a : in the service name)
            if ':' in service:
                # Split service name and package name
                service, package = service.split(':')

                # Check if the package is in the list of updated packages
                regex = '(?:% s)' % '|'.join(updated_packages)

                # If the package is not in the list of updated packages, skip the service
                if not re.match(regex, package):
                    continue

            # If dry-run is enabled, just print the service that would be restarted
            if dry_run:
                print('  ▪ Would restart ' + Fore.YELLOW + service + Style.RESET_ALL)
                continue

            print('  ▪ Restarting ' + Fore.YELLOW + service + Style.RESET_ALL + ':', end=' ')

            # Check if service is active
            result = subprocess.run(
                ["systemctl", "is-active", service],
                stdout = subprocess.PIPE, # subprocess.PIPE & subprocess.PIPE are alias of 'capture_output = True'
                stderr = subprocess.PIPE,
                universal_newlines = True # Alias of 'text = True'
            )

            # If service is unknown or inactive, skip it
            if result.returncode != 0:
                print('service does not exist or is not active')
                continue

            # Restart service
            result = subprocess.run(
                ["systemctl", "restart", service, "--quiet"],
                stdout = subprocess.PIPE, # subprocess.PIPE & subprocess.PIPE are alias of 'capture_output = True'
                stderr = subprocess.PIPE,
                universal_newlines = True # Alias of 'text = True'
            )

            # If service failed to restart, print error message
            if result.returncode != 0:
                print(Fore.RED + 'failed with error: ' + Style.RESET_ALL + result.stderr)
                continue

            print(Fore.GREEN + 'done' + Style.RESET_ALL)
