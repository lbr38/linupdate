# coding: utf-8

# Import libraries
from datetime import datetime
from pathlib import Path
import sys, socket, getpass, subprocess
from colorama import Fore, Style

# Import classes
from src.controllers.App.Config import Config
from src.controllers.System import System

class App:
    #-----------------------------------------------------------------------------------------------
    #
    #   Return current version of the application
    #
    #-----------------------------------------------------------------------------------------------
    def get_version(self):
        try:
            file = open('/opt/linupdate/version', 'r')
            version = file.read()
            file.close()
        except Exception as e:
            version = 'unknown'

        return version


    #-----------------------------------------------------------------------------------------------
    #
    #   Get linupdate daemon agent status
    #
    #-----------------------------------------------------------------------------------------------
    def get_agent_status(self):
        # If systemctl is not installed (e.g. in docker container of linupdate's CI), return disabled
        if not Path('/usr/bin/systemctl').is_file():
            return 'disabled'

        result = subprocess.run(
            ["systemctl", "is-active", "linupdate"],
            stdout = subprocess.PIPE, # subprocess.PIPE & subprocess.PIPE are alias of 'capture_output = True'
            stderr = subprocess.PIPE,
            universal_newlines = True # Alias of 'text = True'
        )

        if result.returncode != 0:
            return 'stopped'

        return 'running'


    #-----------------------------------------------------------------------------------------------
    #
    #   Create lock file
    #
    #-----------------------------------------------------------------------------------------------
    def set_lock(self):
        try:
            Path('/tmp/linupdate.lock').touch()
        except Exception as e:
            raise Exception('Could not create lock file /tmp/linupdate.lock: ' + str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   Remove lock file
    #
    #-----------------------------------------------------------------------------------------------
    def remove_lock(self):
        if not Path('/tmp/linupdate.lock').is_file():
            return

        try:
            Path('/tmp/linupdate.lock').unlink()
        except Exception as e:
            raise Exception('Could not remove lock file /tmp/linupdate.lock: ' + str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   Create base directories
    #
    #-----------------------------------------------------------------------------------------------
    def initialize(self):
        # Create base directories
        try:
            Path('/etc/linupdate').mkdir(parents=True, exist_ok=True)
            Path('/etc/linupdate/modules').mkdir(parents=True, exist_ok=True)
            Path('/opt/linupdate').mkdir(parents=True, exist_ok=True)
            Path('/opt/linupdate/service').mkdir(parents=True, exist_ok=True)
            Path('/var/log/linupdate').mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise Exception('Could not create base directories: ' + str(e))

        # Set permissions
        try:
            Path('/opt/linupdate').chmod(0o750)
            Path('/opt/linupdate/src').chmod(0o750)
            Path('/opt/linupdate/service').chmod(0o750)
            Path('/etc/linupdate').chmod(0o750)
            Path('/etc/linupdate/modules').chmod(0o750)
            Path('/var/log/linupdate').chmod(0o750)
        except Exception as e:
            raise Exception('Could not set permissions to base directories: ' + str(e))

        # Check if the .src directory is empty
        if not len(list(Path('/opt/linupdate/src').rglob('*'))):
            raise Exception('Some linupdate core files are missing, please reinstall linupdate')


    #-----------------------------------------------------------------------------------------------
    #
    #   Print app logo
    #
    #-----------------------------------------------------------------------------------------------
    def print_logo(self):
        space = ' '
        print(space + '                             __                                        ')
        print(space + '.__  .__            ____  __( o`-               .___       __          ')
        print(space + '|  | |__| ____  __ _\   \/  /  \__ ________   __| _/____ _/  |_  ____  ')
        print(space + '|  | |  |/    \|  |  \     /|  |  |  \____ \ / __ |\__  \\   ___/ __ \ ')
        print(space + '|  |_|  |   |  |  |  /     \ ^^|  |  |  |_> / /_/ | / __ \|  | \  ___/ ')
        print(space + '|____|__|___|  |____/___/\  \  |____/|   __/\____ |(____  |__|  \___  >')
        print(space + '             \/           \_/        |__|        \/     \/          \/ ')
        print(Style.DIM + '                                                               ' + self.get_version() + Style.RESET_ALL + '\n')


    #-----------------------------------------------------------------------------------------------
    #
    #   Print system and app summary
    #
    #-----------------------------------------------------------------------------------------------
    def print_summary(self, fromAgent: bool = False):
        myAppConfig = Config()
        mySystem = System()

        # Define execution method
        if fromAgent:
            exec_method = 'automatic (agent)'
        else:
            if not sys.stdin.isatty():
                exec_method = 'automatic (no tty)'
            else:
                exec_method = 'manual (tty)'

        print(' Hostname:            ' + Fore.YELLOW + socket.getfqdn() + Style.RESET_ALL)
        print(' OS:                  ' + Fore.YELLOW + mySystem.get_os_name() + ' ' + mySystem.get_os_version() + Style.RESET_ALL)
        print(' Kernel:              ' + Fore.YELLOW + mySystem.get_kernel() + Style.RESET_ALL)
        print(' Virtualization:      ' + Fore.YELLOW + mySystem.get_virtualization() + Style.RESET_ALL)
        print(' Profile:             ' + Fore.YELLOW + myAppConfig.get_profile() + Style.RESET_ALL)
        print(' Environment:         ' + Fore.YELLOW + myAppConfig.get_environment() + Style.RESET_ALL)
        print(' Execution date:      ' + Fore.YELLOW + datetime.now().strftime('%d-%m-%Y %H:%M:%S') + Style.RESET_ALL)
        print(' Executed by user:    ' + Fore.YELLOW + getpass.getuser() + Style.RESET_ALL + '\n')
        print(' Execution method:    ' + Fore.YELLOW + exec_method + Style.RESET_ALL)
