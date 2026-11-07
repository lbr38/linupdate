# coding: utf-8

"""Application helpers: version, locks, initialization and console output."""

# Import libraries
from datetime import datetime
from pathlib import Path
import sys
import socket
import subprocess
from colorama import Fore, Style

# Import classes
from src.controllers.app.config import Config
from src.controllers.system import System
from src.controllers.lock import Lock
from src.controllers.linupdate_exception import LinupdateException

class App:
    """Application helpers."""
    def get_version(self):
        """Return current version of the application"""
        try:
            with open('/opt/linupdate/version', 'r', encoding='utf-8') as file:
                version = file.read()
        except Exception:
            version = 'unknown'

        return version


    def get_agent_status(self):
        """Get linupdate daemon agent status"""
        # If systemctl is not installed (e.g. in docker container of linupdate's CI), return disabled
        if not Path('/usr/bin/systemctl').is_file():
            return 'disabled'

        result = subprocess.run(
            ["systemctl", "is-active", "linupdate"],
            stdout = subprocess.PIPE, # subprocess.PIPE & subprocess.PIPE are alias of 'capture_output = True'
            stderr = subprocess.PIPE,
            universal_newlines = True, # Alias of 'text = True'
            check = False
        )

        if result.returncode != 0:
            return 'stopped'

        return 'running'


    def set_lock(self):
        """Acquire linupdate run lock (released automatically if the process dies)"""
        try:
            Lock('linupdate', timeout=0).acquire()
        except Exception as e:
            raise LinupdateException('linupdate is already running') from e


    def remove_locks(self):
        """Remove lock files"""
        try:
            Lock('linupdate').release()
        except Exception as e:
            raise LinupdateException('Could not release linupdate lock: ' + str(e)) from e


    def initialize(self):
        """Create base directories"""
        # Create base directories
        try:
            Path('/etc/linupdate').mkdir(parents=True, exist_ok=True)
            Path('/etc/linupdate/modules').mkdir(parents=True, exist_ok=True)
            Path('/opt/linupdate').mkdir(parents=True, exist_ok=True)
            Path('/var/log/linupdate').mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise LinupdateException('Could not create base directories: ' + str(e)) from e

        # Set permissions
        try:
            Path('/opt/linupdate').chmod(0o750)
            Path('/opt/linupdate/src').chmod(0o750)
            Path('/etc/linupdate').chmod(0o750)
            Path('/etc/linupdate/modules').chmod(0o750)
            Path('/var/log/linupdate').chmod(0o750)
        except Exception as e:
            raise LinupdateException('Could not set permissions to base directories: ' + str(e)) from e

        # Check if the .src directory is empty
        if not list(Path('/opt/linupdate/src').rglob('*')):
            raise LinupdateException('Some linupdate core files are missing, please reinstall linupdate')


    def print_logo(self):
        """Print app logo"""
        print('                             __                                         ')
        print('.__  .__            ____  __( o`-               .___       __           ')
        print(r'|  | |__| ____  __ _\   \/  /  \__ ________   __| _/____ _/  |_  ____  ')
        print(r'|  | |  |/    \|  |  \     /|  |  |  \____ \ / __ |\__  \\   ___/ __ \ ')
        print(r'|  |_|  |   |  |  |  /     \ ^^|  |  |  |_> / /_/ | / __ \|  | \  ___/ ')
        print(r'|____|__|___|  |____/___/\  \  |____/|   __/\____ |(____  |__|  \___  >')
        print(r'             \/           \_/        |__|        \/     \/          \/ ')
        print(Style.DIM + '                                                               ' + self.get_version() + Style.RESET_ALL + '\n')


    def print_summary(self):
        """Print system and app summary"""
        my_app_config = Config()
        my_system = System()

        print('Hostname               ' + Fore.YELLOW + socket.getfqdn() + Style.RESET_ALL)
        print('OS                     ' + Fore.YELLOW + my_system.get_os_name() + ' ' + my_system.get_os_version() + Style.RESET_ALL)
        print('Kernel                 ' + Fore.YELLOW + my_system.get_kernel() + Style.RESET_ALL)
        print('Virtualization         ' + Fore.YELLOW + my_system.get_virtualization() + Style.RESET_ALL)
        print('Profile                ' + Fore.YELLOW + my_app_config.get_profile() + Style.RESET_ALL)
        print('Environment            ' + Fore.YELLOW + my_app_config.get_environment() + Style.RESET_ALL)
        print('Execution date         ' + Fore.YELLOW + datetime.now().strftime('%d-%m-%Y %H:%M:%S') + Style.RESET_ALL)
        print('Interactive exec.      ' + Fore.YELLOW + 'Yes' + Style.RESET_ALL + '\n' if sys.stdin.isatty() else 'No' + Style.RESET_ALL + '\n')


    def is_running(self)-> bool:
        """Return true if the application is currently running"""
        return Lock.is_locked('linupdate')

    def tty(self) -> bool:
        """Return true if the application is running in a terminal (tty)"""
        return sys.stdin.isatty()
