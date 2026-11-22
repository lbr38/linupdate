# coding: utf-8

"""APT package manager backend (Debian based systems)."""

# Import libraries
import subprocess
import glob
import os
import re
import sys
import time
import fcntl
from pathlib import Path
import apt
from colorama import Fore, Style

# Import classes
from src.controllers.log_to_file import LogToFile
from src.controllers.app.utils import Utils
from src.controllers.status import update_status, save_status, restore_status
from src.controllers.linupdate_exception import LinupdateException

class Apt:
    """APT package manager backend.

    apt.Cache() opens the cache by itself: calling its open() method again would read all the packages lists a second time
    """
    def __init__(self) -> None:
        # Define some default options
        self.dist_upgrade = False
        self.keep_oldconf = True

        # Packages held by linupdate (and only them) are recorded in this file, so that they can be
        # released by the next run if this one is interrupted, without releasing the packages held by the administrator
        self.holds_file = '/opt/linupdate/tmp/apt-holds'

        # Log file to store each package update output (in a root only directory, never in /tmp, writable by any user)
        self.update_log = '/opt/linupdate/tmp/update-package.log'

        # Packages lists and Release files of all repositories
        self.lists_dir = '/var/lib/apt/lists'

        # Set by update()
        self.summary = None


    def get_security_packages_set(self) -> set:
        """Return a set of package names that have a security update available

        Opens the cache once and simulates an upgrade to check all candidates
        """
        security_set = set()

        try:
            aptcache = apt.Cache()
            aptcache.upgrade(True)

            for pkg in aptcache.get_changes():
                if not pkg.candidate:
                    continue
                if self.is_security_update(pkg):
                    security_set.add(pkg.name)

            aptcache.close()
        except Exception as e:
            # Not blocking, packages are just not flagged as security updates
            print(Fore.YELLOW + 'Could not determine security updates: ' + str(e) + Style.RESET_ALL)

        return security_set


    def is_security_update(self, pkg) -> bool:
        """Return True if candidate package version comes from a security repository"""
        try:
            if not pkg.candidate:
                return False

            for origin in pkg.candidate.origins:
                archive = str(getattr(origin, 'archive', '') or '').lower()
                label = str(getattr(origin, 'label', '') or '').lower()
                site = str(getattr(origin, 'site', '') or '').lower()
                origin_name = str(getattr(origin, 'origin', '') or '').lower()

                if '-security' in archive:
                    return True
                if 'security' in label:
                    return True
                if 'security.debian.org' in site:
                    return True
                if 'debian-security' in origin_name:
                    return True
                if 'ubuntuesm' in origin_name:
                    return True

            return False
        except Exception:
            return False


    def get_current_version(self, package) -> str:
        """Return the current version of a package, empty string if it is not installed"""
        try:
            self.wait_for_dpkg_lock()

            aptcache = apt.Cache()

            try:
                pkg = aptcache[package]

                if not pkg.installed:
                    return ''

                return pkg.installed.version
            finally:
                aptcache.close()

        except Exception as e:
            raise LinupdateException('could not get current version of package ' + package + ': ' + str(e)) from e


    def get_version_repository(self, aptcache, version) -> str:
        """Return the URL of the repository providing a package version (apt.package.Version), 'Unknown' if not found

        Same value as the URL of the 'APT-Sources' field of 'apt show' output.
        python-apt has no public API to get the indexes a version comes from, private attributes are used
        """
        try:
            for package_file, _ in version._cand.file_list:  # pylint: disable=protected-access
                index = aptcache._list.find_index(package_file)  # pylint: disable=protected-access

                # The dpkg status file (installed version) is not the index of a repository
                if index:
                    return index.archive_uri('').rstrip('/')
        except Exception:
            # Informative only, never blocking
            pass

        return 'Unknown'


    def get_source_repository(self, package, version) -> str:
        """Return the URL of the repository providing a version of a package, 'Unknown' if not found"""
        try:
            aptcache = apt.Cache()

            try:
                if package not in aptcache:
                    return 'Unknown'

                package_version = aptcache[package].versions.get(version)

                if package_version is None:
                    return 'Unknown'

                return self.get_version_repository(aptcache, package_version)
            finally:
                aptcache.close()

        except Exception as e:
            raise LinupdateException('could not get source repository for package ' + package + ' version ' + version + ': ' + str(e)) from e


    def get_available_version(self, package) -> str:
        """Return the available version of an installed package, empty string if it is not installed or has no candidate"""
        try:
            self.wait_for_dpkg_lock()

            aptcache = apt.Cache()

            try:
                pkg = aptcache[package]

                if not pkg.installed or not pkg.candidate:
                    return ''

                return pkg.candidate.version
            finally:
                aptcache.close()

        except Exception as e:
            raise LinupdateException('could not get available version of package ' + package + ': ' + str(e)) from e


    def get_installed_packages(self) -> list:
        """Return list of installed apt packages, sorted by name"""
        packages_list = []

        try:
            aptcache = apt.Cache()

            try:
                for pkg in aptcache:
                    if pkg.installed:
                        packages_list.append({
                            'name': pkg.name,
                            'version': pkg.installed.version,
                        })
            finally:
                aptcache.close()

        except Exception as e:
            raise LinupdateException('could not get installed packages: ' + str(e)) from e

        # Sort the list by package name
        packages_list.sort(key=lambda x: x['name'])

        return packages_list


    def get_available_packages(self, dist_upgrade: bool = False) -> list:
        """Return list of available apt packages, sorted by name"""
        packages_list = []

        aptcache = apt.Cache()

        try:
            # Simulate an upgrade to get the list of available packages
            aptcache.upgrade(dist_upgrade)

            # Loop through all packages marked for upgrade
            for pkg in aptcache.get_changes():
                # Skip malformed entries without installed/candidate versions, and packages that are not upgraded (e.g. removed)
                if not pkg.candidate or not pkg.installed or not pkg.is_upgradable:
                    continue

                packages_list.append({
                    'name': pkg.name,
                    'current_version': pkg.installed.version,
                    'target_version': pkg.candidate.version,
                    'repository': self.get_version_repository(aptcache, pkg.candidate),
                    'security': self.is_security_update(pkg)
                })
        finally:
            aptcache.close()

        # Sort the list by package name
        packages_list.sort(key=lambda x: x['name'])

        return packages_list


    def is_installed(self, package) -> bool:
        """Return True if a package is installed"""
        try:
            aptcache = apt.Cache()

            try:
                return package in aptcache and aptcache[package].is_installed
            finally:
                aptcache.close()

        except Exception as e:
            raise LinupdateException('could not check if package ' + package + ' is installed: ' + str(e)) from e


    def wait_for_dpkg_lock(self, timeout: int = 60) -> None:
        """Wait for dpkg lock to be released

        Default timeout is 60 seconds
        """
        lock_files = [
            '/var/lib/dpkg/lock',
            '/var/lib/dpkg/lock-frontend',
            '/var/cache/apt/archives/lock',
            '/var/lib/apt/lists/lock'
        ]

        # Save status message
        save_status()

        start_time = time.time()

        while time.time() - start_time < timeout:
            locks_held = False
            for lock_file in lock_files:
                if os.path.exists(lock_file):
                    try:
                        with open(lock_file, 'w', encoding='utf-8') as handle:
                            fcntl.lockf(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except IOError:
                        locks_held = True
                        break

            if not locks_held:
                # Restore status message
                restore_status()
                return

            update_status("Waiting for dpkg lock to be released")
            time.sleep(2)

        raise LinupdateException(f'Could not acquire dpkg lock within {timeout} seconds')


    def clear_cache(self) -> None:
        """Clear apt cache: downloaded packages and packages lists of all repositories

        Last resort when the cache is inconsistent, all the packages lists are downloaded again by the next cache update.
        Lock files are kept: deleting a lock file held by a running apt process would let another one run at the same time
        """
        self.wait_for_dpkg_lock()

        # Delete downloaded packages and binary caches (/var/cache/apt/archives/, pkgcache.bin, srcpkgcache.bin)
        result = subprocess.run(
            ['apt-get', 'clean'],
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE,
            universal_newlines = True,
            check = False
        )

        if result.returncode != 0:
            raise LinupdateException('could not clear apt cache: ' + result.stderr.strip())

        # Delete packages lists and Release files of all repositories
        try:
            for path in Path(self.lists_dir).iterdir():
                if path.is_file() and path.name != 'lock':
                    path.unlink()
        except Exception as e:
            raise LinupdateException('could not clear ' + self.lists_dir + ': ' + str(e)) from e


    def update_cache(self) -> None:
        """Update apt cache (packages lists of all repositories)"""
        self.wait_for_dpkg_lock()

        try:
            result = subprocess.run(
                ['apt-get', 'update'],
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE,
                universal_newlines = True,
                check = False
            )
        except Exception as e:
            raise LinupdateException('could not update apt cache: ' + str(e)) from e

        if result.returncode != 0:
            raise LinupdateException('could not update apt cache: ' + result.stderr.strip())

        # apt-get update also succeeds when some repositories could not be refreshed: their previous packages lists are kept,
        # so the available packages may be outdated. Print its warnings instead of hiding them
        if result.stderr.strip():
            print(Fore.YELLOW + result.stderr.strip() + Style.RESET_ALL)


    def get_exclusion(self) -> list:
        """Get list of excluded packages (hold)"""
        result = subprocess.run(
            ["apt-mark", "showhold"],
            stdout = subprocess.PIPE, # subprocess.PIPE & subprocess.PIPE are alias of 'capture_output = True'
            stderr = subprocess.PIPE,
            universal_newlines = True, # Alias of 'text = True'
            check = False
        )

        if result.returncode != 0:
            raise LinupdateException('could not get excluded (holded) packages list:' + result.stderr)

        return result.stdout.splitlines()


    def get_linupdate_holds(self) -> list:
        """Get list of packages held by linupdate"""
        if not Path(self.holds_file).is_file():
            return []

        try:
            with open(self.holds_file, 'r', encoding='utf-8') as file:
                return [line.strip() for line in file if line.strip()]
        except Exception as e:
            raise LinupdateException('could not read ' + self.holds_file + ': ' + str(e)) from e


    def exclude(self, package) -> None:
        """Exclude (hold) specified package"""
        # A package already held (by the administrator) is already excluded: leave it as it is,
        # so that it stays held after the update
        if package in self.get_exclusion():
            return

        # Record the package before holding it, so that it is released even if linupdate is interrupted right after
        try:
            Path(self.holds_file).parent.mkdir(parents=True, exist_ok=True)
            with open(self.holds_file, 'a', encoding='utf-8') as file:
                file.write(package + '\n')
        except Exception as e:
            raise LinupdateException('could not record ' + package + ' package exclusion in ' + self.holds_file + ': ' + str(e)) from e

        result = subprocess.run(
            ["apt-mark", "hold", package],
            stdout = subprocess.PIPE, # subprocess.PIPE & subprocess.PIPE are alias of 'capture_output = True'
            stderr = subprocess.PIPE,
            universal_newlines = True, # Alias of 'text = True'
            check = False
        )

        if result.returncode != 0:
            raise LinupdateException('could not exclude ' + package + ' package from update: ' + result.stderr)


    def remove_all_exclusions(self) -> None:
        """Remove the package exclusions set by linupdate (unhold), packages held by the administrator stay held"""
        linupdate_holds = self.get_linupdate_holds()

        # Quit if linupdate has not held any package
        if not linupdate_holds:
            return

        # Retrieve the list of packages on hold
        held_packages = self.get_exclusion()

        # Unhold the packages held by linupdate (skip those which are not held anymore, e.g. removed packages)
        for package in linupdate_holds:
            if package not in held_packages:
                continue

            result = subprocess.run(
                ["apt-mark", "unhold", package],
                stdout = subprocess.PIPE, # subprocess.PIPE & subprocess.PIPE are alias of 'capture_output = True'
                stderr = subprocess.PIPE,
                universal_newlines = True, # Alias of 'text = True'
                check = False
            )

            if result.returncode != 0:
                raise LinupdateException('could not unhold packages: ' + package)

        try:
            Path(self.holds_file).unlink()
        except Exception as e:
            raise LinupdateException('could not remove ' + self.holds_file + ': ' + str(e)) from e


    def update(self, packages_list, exit_on_package_update_error: bool = True, dry_run: bool = False) -> None:
        """Update packages"""
        counter = 0
        update_status_msg = 'Updating packages'

        # If dry-run, add it to the status message
        if dry_run:
            update_status_msg += ' (dry run)'

        log = self.update_log
        Path(log).parent.mkdir(parents=True, exist_ok=True)

        # Package update summary
        self.summary = {
            'update': {
                'success': {
                    'count': 0,
                    'packages': {}
                },
                'failed': {
                    'count': 0,
                    'packages': {}
                }
            }
        }

        # Count the number of packages to update
        packages_to_update_count = 0
        for pkg in packages_list:
            if pkg['install']:
                packages_to_update_count += 1

        # Loop through the list of packages to update
        for pkg in packages_list:
            # If the package is marked as not to install, skip it
            if not pkg['install']:
                continue

            counter += 1
            update_status(update_status_msg + ' (' + str(counter) + '/' + str(packages_to_update_count ) + ')')

            # If log file exists, remove it
            if Path(log).is_file():
                Path(log).unlink()

            with LogToFile(log):
                print('\n▪ Updating ' + Fore.GREEN + pkg['name'] + Style.RESET_ALL + ' (' + pkg['current_version'] + ' → ' + pkg['target_version'] + '):')

                # Before updating, check If package is already in the latest version, if so, skip it
                # It means that it has been updated previously by another package, probably because it was a dependency
                # Retrieve current version
                current_version = self.get_current_version(pkg['name'])

                # If current version is the same the target version, skip the update
                if current_version == pkg['target_version']:
                    print(Fore.GREEN + '✔ ' + Style.RESET_ALL + pkg['name'] + ' is already up to date (updated with another package).')

                    # Mark the package as already updated
                    self.summary['update']['success']['count'] += 1

                    # Also add the package to the list of successful packages
                    self.summary['update']['success']['packages'][pkg['name']] = {
                        'version': pkg['target_version'],
                        'log': 'Already up to date (updated with another package).'
                    }

                    # Continue to the next package
                    continue

                # Define the command to update the package
                # DPkg::Lock::Timeout makes apt-get wait for the dpkg lock instead of failing at once when another process
                # (e.g. packagekitd) grabs it between two package updates (apt >= 1.9.11, ignored by older versions)
                cmd = 'DEBIAN_FRONTEND=noninteractive /usr/bin/apt-get install ' + pkg['name'] + '=' + pkg['target_version'] +  ' -y'
                cmd += ' -o DPkg::Lock::Timeout=120'

                # If --keep-oldconf is True, then keep the old configuration files
                if self.keep_oldconf:
                    cmd += ' -o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold'

                # If --dry-run is True, then simulate the update
                if dry_run:
                    cmd += ' --dry-run'

                # Leaving the 'with' block closes the pipe and waits for the command to finish
                with subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    shell = True
                ) as popen:
                    # Print lines as they are read
                    for line in popen.stdout:
                        # Deal with carriage return
                        parts = line.split('\r')
                        for part in parts[:-1]:
                            sys.stdout.write('\r' + '| ' + part.strip() + '\n')
                            sys.stdout.flush()
                        buffer = parts[-1]
                        sys.stdout.write('\r' + '| ' + buffer.strip() + '\n')
                        sys.stdout.flush()

                # Deal with the carriage return of the last line
                sys.stdout.write('\r')

                # Get log content
                with open(log, 'r', encoding='utf-8') as file:
                    log_content = Utils().clean_log(file.read())

                # If command failed, either raise an exception or print a warning
                if popen.returncode != 0:
                    # Add the package to the list of failed packages
                    self.summary['update']['failed']['count'] += 1

                    # Add the package to the list of failed packages
                    self.summary['update']['failed']['packages'][pkg['name']] = {
                        'version': pkg['target_version'],
                        'log': log_content
                    }

                    # If error is critical, raise an exception
                    if exit_on_package_update_error:
                        raise LinupdateException('Error while updating ' + pkg['name'] + '.')

                    # Else print an error message and continue to the next package
                    print(Fore.RED + '✕ ' + Style.RESET_ALL + 'Error while updating ' + pkg['name'] + '.')
                    continue

                # If command succeeded, increment the success counter
                self.summary['update']['success']['count'] += 1

                # Add the package to the list of successful packages
                self.summary['update']['success']['packages'][pkg['name']] = {
                    'version': pkg['target_version'],
                    'log': log_content
                }

                # Print a success message
                if dry_run:
                    print(Fore.GREEN + '✔ ' + Style.RESET_ALL + pkg['name'] + ' would be updated (dry run).')
                else:
                    print(Fore.GREEN + '✔ ' + Style.RESET_ALL + pkg['name'] + ' updated successfully.')


    def get_history(self, order) -> list:
        """Return apt history log files sorted by modification time"""
        try:
            files = sorted(glob.glob('/var/log/apt/history.log*'), key=os.path.getmtime)

            # If order is newest, then sort by date in ascending order
            if order == 'newest':
                files.reverse()
        except Exception as e:
            raise LinupdateException('could not get apt history log files: ' + str(e)) from e

        del order

        return files


    def parse_history(self, history_files: list, entries_limit: int) -> list:
        """Parse all apt history log files and return a list of events (JSON)"""
        # Initialize a limit counter which will be incremented until it reaches the entries_limit
        limit_counter = 0

        # Initialize a list of events
        events = []

        # Parse each apt history files
        for history_file in history_files:
            # Quit if the limit of entries to send has been reached
            if limit_counter >= entries_limit:
                break

            # If file is empty (e.g. file has been rotated), ignore it
            if os.stat(history_file).st_size == 0:
                continue

            # Retrieve all Start-Date in the history file
            result = subprocess.run(
                ['zgrep "^Start-Date:*" ' + history_file],
                stdout = subprocess.PIPE, # subprocess.PIPE & subprocess.PIPE are alias of 'capture_output = True'
                stderr = subprocess.PIPE,
                universal_newlines = True, # Alias of 'text = True'
                shell = True,
                check = False
            )

            # Quit if an error occurred
            if result.returncode != 0:
                raise LinupdateException('no result matching the pattern "Start-Date" in file ' + history_file)

            # Split the result into a list
            start_dates = result.stdout.strip().split('\n')

            for start_date in start_dates:
                # Reset all variables for each event
                installed_packages = ''
                upgraded_packages = ''
                removed_packages = ''
                purged_packages = ''
                downgraded_packages = ''
                reinstalled_packages = ''
                installed_packages_json = ''
                upgraded_packages_json = ''
                removed_packages_json = ''
                purged_packages_json = ''
                downgraded_packages_json = ''
                reinstalled_packages_json = ''

                # Quit if the limit of entries to send has been reached
                if limit_counter >= entries_limit:
                    break

                # Retrieve the event block : from the start date (START_DATE) to the next empty line
                # If the file is compressed, we must use zcat to read it
                if history_file.endswith('.gz'):
                    result = subprocess.run(
                        ['zcat ' + history_file + ' | sed -n "/' + start_date + '/,/^$/p"'],
                        stdout = subprocess.PIPE, # subprocess.PIPE & subprocess.PIPE are alias of 'capture_output = True'
                        stderr = subprocess.PIPE,
                        universal_newlines = True, # Alias of 'text = True'
                        shell = True,
                        check = False
                    )

                # If the file is not compressed, we can use sed directly
                else:
                    result = subprocess.run(
                        ['sed -n "/' + start_date + '/,/^$/p" ' + history_file],
                        stdout = subprocess.PIPE, # subprocess.PIPE & subprocess.PIPE are alias of 'capture_output = True'
                        stderr = subprocess.PIPE,
                        universal_newlines = True, # Alias of 'text = True'
                        shell = True,
                        check = False
                    )

                if result.returncode != 0:
                    raise LinupdateException('no event found for date "' + start_date + '" in file ' + history_file)

                # Retrieve event block lines
                event = result.stdout.strip()

                # From the retrieved event block, we can get the start date and time and the end date and time
                # If the event block does not contain a Start-Date or an End-Date, ignore the event (the event might be
                # incomplete because the log file was being written at the same time)
                if not re.search(r'^Start-Date: (.+)', event):
                    continue
                if not re.search(r'End-Date: (.+)', event):
                    continue

                date_start = re.search(r'^Start-Date: (.+)', event).group(1).split()[0].strip()
                time_start = re.search(r'^Start-Date: (.+)', event).group(1).split()[1].strip()
                date_end = re.search(r'End-Date: (.+)', event).group(1).split()[0].strip()
                time_end = re.search(r'End-Date: (.+)', event).group(1).split()[1].strip()

                # Retrieve the event command, ignore event if no command found
                if not re.search(r'Commandline: (.+)', event):
                    continue

                command = re.search(r'Commandline: (.+)', event).group(1).strip()

                # Retrieve packages installed, removed, upgraded, downgraded, etc.
                if re.search(r'Install: (.+)', event):
                    installed_packages = re.search(r'Install: (.+)', event).group(1).strip()
                if re.search(r'Upgrade: (.+)', event):
                    upgraded_packages = re.search(r'Upgrade: (.+)', event).group(1).strip()
                if re.search(r'Remove: (.+)', event):
                    removed_packages = re.search(r'Remove: (.+)', event).group(1).strip()
                if re.search(r'Purge: (.+)', event):
                    purged_packages = re.search(r'Purge: (.+)', event).group(1).strip()
                if re.search(r'Downgrade: (.+)', event):
                    downgraded_packages = re.search(r'Downgrade: (.+)', event).group(1).strip()
                if re.search(r'Reinstall: (.+)', event):
                    reinstalled_packages = re.search(r'Reinstall: (.+)', event).group(1).strip()

                # Parse packages lists and convert them to JSON
                if installed_packages != '':
                    installed_packages_json = self.parse_packages_line_to_json(installed_packages, 'install')

                if upgraded_packages != '':
                    upgraded_packages_json = self.parse_packages_line_to_json(upgraded_packages, 'upgrade')

                if removed_packages != '':
                    removed_packages_json = self.parse_packages_line_to_json(removed_packages, 'remove')

                if purged_packages != '':
                    purged_packages_json = self.parse_packages_line_to_json(purged_packages, 'purge')

                if downgraded_packages != '':
                    downgraded_packages_json = self.parse_packages_line_to_json(downgraded_packages, 'downgrade')

                if reinstalled_packages != '':
                    reinstalled_packages_json = self.parse_packages_line_to_json(reinstalled_packages, 'reinstall')

                # Create the event JSON object
                event = {
                    'date_start': date_start,
                    'time_start': time_start,
                    'date_end': date_end,
                    'time_end': time_end,
                    'command': command
                }

                if installed_packages_json != '':
                    event['installed'] = installed_packages_json

                if upgraded_packages_json != '':
                    event['upgraded'] = upgraded_packages_json

                if removed_packages_json != '':
                    event['removed'] = removed_packages_json

                if purged_packages_json != '':
                    event['purged'] = purged_packages_json

                if downgraded_packages_json != '':
                    event['downgraded'] = downgraded_packages_json

                if reinstalled_packages_json != '':
                    event['reinstalled'] = reinstalled_packages_json

                # Add the event to the list of events
                events.append(event)

                limit_counter += 1

                del installed_packages, upgraded_packages, removed_packages, purged_packages
                del downgraded_packages, reinstalled_packages, installed_packages_json
                del upgraded_packages_json, removed_packages_json, purged_packages_json
                del downgraded_packages_json, reinstalled_packages_json, event
                del date_start, time_start, date_end, time_end
                del command

            del history_file, result, start_dates

        del history_files

        return events


    def parse_packages_line_to_json(self, packages: str, action: str) -> list:
        """Parse a string of one or multiple package(s) into a list of JSON objects"""
        packages_json = []

        # If there is more than one package on the same line
        # e.g.
        # libc6-i386:amd64 (2.35-0ubuntu3.7, 2.35-0ubuntu3.8), libc6:amd64 (2.35-0ubuntu3.7, 2.35-0ubuntu3.8), libc6:i386 (2.35-0ubuntu3.7, 2.35-0ubuntu3.8), libc-dev-bin:amd64 (2.35-0ubuntu3.7, 2.35-0ubuntu3.8), libc6-dbg:amd64 (2.35-0ubuntu3.7, 2.35-0ubuntu3.8), libc6-dev:amd64 (2.35-0ubuntu3.7, 2.35-0ubuntu3.8)
        if re.search(r"\),", packages):
            # Split all the packages from the same line into a list
            packages = re.sub(r"\),", "\n", packages).split('\n')

        # Else if there is only one package on the same line, just split the line into a list
        else:
            packages = packages.split('\n')

        # For all packages in the list, retrieve the name and the version
        for package in packages:
            # First, remove extra spaces
            package = package.strip()

            # Then, split the package into name and version
            name = package.split(' ')[0]

            # Depending on the action, the version to retrieve is on a different position
            if action in ('install', 'remove', 'purge', 'reinstall'):
                version = package.split(' ')[1]
            if action in ('upgrade', 'downgrade'):
                version = package.split(' ')[2]

            # Remove parenthesis, commas, colons and spaces from name and version
            for char in ['(', ')', ',', ' ']:
                name = name.replace(char, '')
                version = version.replace(char, '')

            # Also remove architecture suffix from name
            # A Debian package name cannot contain ':', so everything after it is the architecture (e.g. libc6:amd64 => libc6)
            name = name.split(':')[0]

            # If package name is empty (should not happen), ignore it
            if name == '':
                continue

            # If version is empty (sometimes it can be), set it to 'unknown'
            if version == '':
                version = 'unknown'

            # Add the package to the list of packages
            packages_json.append({
                'name': name,
                'version': version
            })

            del name, version, char

        del packages, action

        # Return the list of packages as JSON
        return packages_json
