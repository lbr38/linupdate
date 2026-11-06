# coding: utf-8

"""Application helpers: version, locks, initialization and console output."""

# Import libraries
from datetime import datetime
from pathlib import Path
import sys
import socket
import subprocess
from typing import Any, Optional
from colorama import Fore, Style

# Import classes
from src.controllers.app.config import Config
from src.controllers.system import System
from src.controllers.lock import Lock
from src.controllers.linupdate_exception import LinupdateException

# Date of the last successful packages update (removed on package uninstall, see packaging scripts)
LAST_UPDATE_FILE = '/opt/linupdate/last-update'

# Date format used in summary and last update file
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

class App:
    """Application helpers."""
    def get_version(self) -> str:
        """Return current version of the application"""
        try:
            with open('/opt/linupdate/version', 'r', encoding='utf-8') as file:
                version = file.read()
        except Exception:
            version = 'unknown'

        return version


    def get_agent_status(self) -> str:
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


    def set_lock(self) -> None:
        """Acquire linupdate run lock (released automatically if the process dies)"""
        try:
            Lock('linupdate', timeout=0).acquire()
        except Exception as e:
            raise LinupdateException('linupdate is already running') from e


    def remove_locks(self) -> None:
        """Remove lock files"""
        try:
            Lock('linupdate').release()
        except Exception as e:
            raise LinupdateException('Could not release linupdate lock: ' + str(e)) from e


    def initialize(self) -> None:
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


    def print_logo(self) -> None:
        """Print app logo"""
        print('                             __                                         ')
        print('.__  .__            ____  __( o`-               .___       __           ')
        print(r'|  | |__| ____  __ _\   \/  /  \__ ________   __| _/____ _/  |_  ____  ')
        print(r'|  | |  |/    \|  |  \     /|  |  |  \____ \ / __ |\__  \\   ___/ __ \ ')
        print(r'|  |_|  |   |  |  |  /     \ ^^|  |  |  |_> / /_/ | / __ \|  | \  ___/ ')
        print(r'|____|__|___|  |____/___/\  \  |____/|   __/\____ |(____  |__|  \___  >')
        print(r'             \/           \_/        |__|        \/     \/          \/ ')
        print(Style.DIM + '                                                               ' + self.get_version() + Style.RESET_ALL + '\n')


    def get_last_update(self) -> Optional[datetime]:
        """Return the date of the last successful packages update, or None if unknown"""
        if not Path(LAST_UPDATE_FILE).is_file():
            return None

        with open(LAST_UPDATE_FILE, 'r', encoding='utf-8') as file:
            return datetime.strptime(file.read().strip(), DATE_FORMAT)


    def set_last_update(self) -> None:
        """Save the current date as the last successful packages update date (never stops the execution)"""
        try:
            with open(LAST_UPDATE_FILE, 'w', encoding='utf-8') as file:
                file.write(datetime.now().strftime(DATE_FORMAT) + '\n')
        except Exception as e:
            print(' ' + Fore.YELLOW + 'Could not save last update date: ' + str(e) + Style.RESET_ALL)


    def print_summary(self, args = None) -> None:
        """Print system and app summary

        Every value is retrieved independently: if one fails, 'Unknown' is printed and the execution continues
        """
        debug = getattr(args, 'debug', False)

        def safe(getter, default = 'Unknown') -> Any:
            """Return getter() result, or default if it raises"""
            try:
                return getter()
            except Exception as e:
                if debug:
                    print(' ' + Fore.YELLOW + 'Summary: ' + str(e) + Style.RESET_ALL)
                return default

        try:
            my_system = System()
            my_app_config = safe(Config, None)

            sections = [
                ('System', [
                    ('Hostname', socket.getfqdn),
                    ('IP address', lambda: self._summary_ip(my_system)),
                    ('OS', lambda: self._summary_os(my_system, safe)),
                    ('Kernel', my_system.get_kernel),
                    ('Uptime', lambda: self._format_duration(datetime.now().timestamp() - my_system.get_uptime())),
                    ('Reboot pending', lambda: Fore.YELLOW + 'Yes' + Style.RESET_ALL if my_system.reboot_required() else 'No'),
                ]),
                ('Execution', [
                    # Lambdas: my_app_config may be None, it must only fail when the row is printed
                    ('Profile', lambda: my_app_config.get_profile()),           # pylint: disable=unnecessary-lambda
                    ('Environment', lambda: my_app_config.get_environment()),   # pylint: disable=unnecessary-lambda
                    ('Mode', lambda: self._summary_mode(args)),
                    ('Exclusions', lambda: self._summary_exclusions(my_app_config, args)),
                    ('Modules', lambda: self._join_list(my_app_config.get_conf()['modules']['enabled'])),
                    ('Mail report', lambda: self._summary_mail(my_app_config)),
                    ('Date', lambda: datetime.now().strftime(DATE_FORMAT)),
                ]),
            ]

            # Align all values on the longest label
            width = max(len(label) for _, rows in sections for label, _ in rows) + 3

            for title, rows in sections:
                print(' ' + Style.BRIGHT + title + Style.RESET_ALL)

                for label, getter in rows:
                    values = safe(getter)

                    # A getter can return several lines (e.g. exclusions)
                    if not isinstance(values, list):
                        values = [values]

                    for i, value in enumerate(values):
                        print('   ' + Style.DIM + (label if i == 0 else '').ljust(width) + Style.RESET_ALL + str(value) + Style.RESET_ALL)

                print()

        # The summary is informative only, it must never stop the execution
        except Exception as e:
            print(' ' + Fore.YELLOW + 'Could not print summary: ' + str(e) + Style.RESET_ALL + '\n')


    def _summary_ip(self, my_system) -> str:
        """Return the main IP address and its interface"""
        ip, iface = my_system.get_main_ip()

        if not ip:
            return 'Unknown'

        return ip + ' (' + iface + ')'


    def _summary_os(self, my_system, safe) -> str:
        """Return OS name, version, architecture and virtualization"""
        details = [safe(my_system.get_arch)]

        virtualization = safe(my_system.get_virtualization)
        if virtualization != 'Unknown':
            details.append(virtualization)

        return my_system.get_os_name() + ' ' + my_system.get_os_version() + ' (' + ', '.join(details) + ')'


    def _summary_mode(self, args) -> str:
        """Return execution mode and enabled options"""
        mode = ['interactive' if sys.stdin.isatty() else 'non-interactive']

        if args is None:
            return mode[0]

        if getattr(args, 'dry_run', False):
            mode.append(Fore.YELLOW + 'dry-run' + Style.RESET_ALL)
        if getattr(args, 'check_updates', False):
            mode.append('check-updates')
        if getattr(args, 'dist_upgrade', False):
            mode.append('dist-upgrade')
        if getattr(args, 'assume_yes', False):
            mode.append('assume-yes')
        if getattr(args, 'ignore_exclusions', False):
            mode.append(Fore.YELLOW + 'ignore-exclusions' + Style.RESET_ALL)
        if getattr(args, 'clear_cache', False):
            mode.append('clear-cache')
        if getattr(args, 'reboot', False):
            mode.append('auto-reboot')

        packages = getattr(args, 'packages_to_update', [])
        if packages:
            mode.append('packages: ' + self._join_list([package['name'] for package in packages]))

        return ', '.join(mode)


    def _summary_exclusions(self, my_app_config, args) -> list:
        """Return packages excluded from update"""
        lines = []

        always = my_app_config.get_exclusion()
        if always:
            lines.append('always: ' + self._join_list(always))

        major = my_app_config.get_major_exclusion()
        if major:
            lines.append('on major update: ' + self._join_list(major))

        if lines and getattr(args, 'ignore_exclusions', False):
            lines[0] += Fore.YELLOW + ' (ignored)' + Style.RESET_ALL

        if not lines:
            lines = ['None']

        # Imported here: the reposerver module imports the package controller, which imports this file
        from src.controllers.module.reposerver.config import Config as ReposerverConfig # pylint: disable=import-outside-toplevel

        # The local exclusions are replaced by the reposerver profile ones before the update
        if ReposerverConfig.packages_conf_from_reposerver_enabled(my_app_config.get_conf()):
            lines.append(Fore.YELLOW + '(will be replaced by the reposerver profile exclusions)' + Style.RESET_ALL)

        return lines


    def _summary_mail(self, my_app_config) -> str:
        """Return mail report status and recipients"""
        if not my_app_config.get_mail_enabled():
            return 'Disabled'

        recipients = my_app_config.get_mail_recipient()
        if not recipients:
            return Fore.YELLOW + 'Enabled (no recipient)' + Style.RESET_ALL

        return 'Enabled (' + self._join_list(recipients) + ')'


    def _summary_last_update(self) -> str:
        """Return last successful packages update date and elapsed time"""
        last_update = self.get_last_update()

        if last_update is None:
            return 'Unknown'

        elapsed = (datetime.now() - last_update).total_seconds()

        return last_update.strftime(DATE_FORMAT) + ' (' + self._format_duration(elapsed) + ' ago)'


    def _join_list(self, items, limit: int = 5) -> str:
        """Join a list as a string, truncated after 'limit' items"""
        if not items:
            return 'None'

        items = [str(item) for item in items]

        if len(items) > limit:
            return ', '.join(items[:limit]) + ' (+' + str(len(items) - limit) + ' more)'

        return ', '.join(items)


    def _format_duration(self, seconds: float) -> str:
        """Return a human readable duration (e.g. '3 days, 4 hours')"""
        def plural(count, word) -> str:
            return str(count) + ' ' + word + ('s' if count > 1 else '')

        days, remainder = divmod(max(int(seconds), 0), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes = remainder // 60

        if days:
            return plural(days, 'day') + ', ' + plural(hours, 'hour')

        if hours:
            return plural(hours, 'hour') + ', ' + plural(minutes, 'minute')

        if minutes:
            return plural(minutes, 'minute')

        return 'less than a minute'


    def is_running(self)-> bool:
        """Return true if the application is currently running"""
        return Lock.is_locked('linupdate')

    def tty(self) -> bool:
        """Return true if the application is running in a terminal (tty)"""
        return sys.stdin.isatty()
