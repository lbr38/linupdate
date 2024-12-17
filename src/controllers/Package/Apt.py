# coding: utf-8

# Import libraries
import apt
import subprocess
import glob
import os
import re
import sys
import time
import fcntl
from colorama import Fore, Style
from pathlib import Path

# Import classes
from src.controllers.Log import Log
from src.controllers.App.Utils import Utils

class Apt:
    def __init__(self):
        # Create an instance of the apt cache
        self.aptcache = apt.Cache()

        # Define some default options
        self.dist_upgrade = False
        self.keep_oldconf = True


    #-----------------------------------------------------------------------------------------------
    #
    #   Return the current version of a package
    #
    #-----------------------------------------------------------------------------------------------
    def get_current_version(self, package):
        try:
            # Open apt cache
            self.aptcache.open(None)

            # Get the package from the cache
            pkg = self.aptcache[package]

            # If the package is not installed, return an empty string
            if not pkg.is_installed:
                return ''

            # Return the installed version of the package
            return pkg.installed.version

        except Exception as e:
            raise Exception('could not get current version of package ' + package + ': ' + str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   Return the available version of a package
    #
    #-----------------------------------------------------------------------------------------------
    def get_available_version(self, package):
        try:
            # Open apt cache
            self.aptcache.open(None)

            # Get the package from the cache
            pkg = self.aptcache[package]

            # If the package is not installed, return an empty string
            if not pkg.is_installed:
                return ''

            # Return the available version of the package
            return pkg.candidate.version

        except Exception as e:
            raise Exception('could not get available version of package ' + package + ': ' + str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   Return list of installed apt packages, sorted by name
    #
    #-----------------------------------------------------------------------------------------------
    def get_installed_packages(self):
        list = []

        # Clear, update cache and open it
        # TODO to fix: cache is updated twice because of a weird bug I cannot fix. It seems that the cache is not updated correctly the first time and leads to an empty list of packages.
        self.update_cache()
        self.update_cache()

        try:
            # Loop through all installed packages
            for pkg in self.aptcache:
                # If the package is installed, add it to the list of installed packages
                if pkg.is_installed:
                    list.append({
                        'name': pkg.name,
                        'version': pkg.installed.version,
                    })
            
            # Sort the list by package name
            list.sort(key=lambda x: x['name'])
        
        except Exception as e:
            raise Exception('could not get installed packages: ' + str(e))

        return list


    #-----------------------------------------------------------------------------------------------
    #
    #   Return list of available apt packages, sorted by name
    #
    #-----------------------------------------------------------------------------------------------
    def get_available_packages(self, dist_upgrade: bool = False):
        list = []

        # Clear, update cache and open it
        # TODO to fix: cache is updated twice because of a weird bug I cannot fix. It seems that the cache is not updated correctly the first time and leads to an empty list of packages.
        # Might be because /etc/apt/sources.list is empty
        self.update_cache()
        self.update_cache()

        # Simulate an upgrade to get the list of available packages
        self.aptcache.upgrade(dist_upgrade)

        # Loop through all packages marked for upgrade
        for pkg in self.aptcache.get_changes():
            # If the package is upgradable, add it to the list of available packages
            if pkg.is_upgradable:
                myPackage = {
                    'name': pkg.name,
                    'current_version': pkg.installed.version,
                    'target_version': pkg.candidate.version
                }

                list.append(myPackage)
        
        # Sort the list by package name
        list.sort(key=lambda x: x['name'])
        
        return list


    #-----------------------------------------------------------------------------------------------
    #
    #   Wait for dpkg lock to be released
    #   Default timeout is 60 seconds
    #
    #-----------------------------------------------------------------------------------------------
    def wait_for_dpkg_lock(self, timeout: int = 60):
        lock_files = [
            '/var/lib/dpkg/lock',
            '/var/lib/dpkg/lock-frontend',
            '/var/cache/apt/archives/lock',
            '/var/lib/apt/lists/lock'
        ]

        start_time = time.time()

        while time.time() - start_time < timeout:
            locks_held = False
            for lock_file in lock_files:
                if os.path.exists(lock_file):
                    try:
                        with open(lock_file, 'w') as handle:
                            fcntl.lockf(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except IOError:
                        locks_held = True
                        break

            if not locks_held:
                return

            print(' Waiting for dpkg lock to be released...')
            time.sleep(5)

        raise Exception(f'Could not acquire dpkg lock within {timeout} seconds')


    #-----------------------------------------------------------------------------------------------
    #
    #   Clear apt cache
    #
    #-----------------------------------------------------------------------------------------------
    def clear_cache(self):
        try:
            # Wait for the lock to be released
            self.wait_for_dpkg_lock()

            self.aptcache.clear()
        except Exception as e:
            raise Exception('could not clear apt cache: ' + str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   Update apt cache
    #
    #-----------------------------------------------------------------------------------------------
    def update_cache(self):
        try:
            # Clear cache
            self.wait_for_dpkg_lock()
            self.clear_cache()
        except Exception as e:
            raise Exception('unable to clear apt cache: ' + str(e))

        try:
            # Update cache
            self.wait_for_dpkg_lock()
            self.aptcache.update()
        except Exception as e:
            raise Exception('could not update apt cache: ' + str(e))

        try:
            # Reopen cache
            self.wait_for_dpkg_lock()
            self.aptcache.open(None)
        except Exception as e:
            raise Exception('could not open apt cache: ' + str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   Get list of excluded packages (hold)
    #
    #-----------------------------------------------------------------------------------------------
    def get_exclusion(self):
        result = subprocess.run(
            ["apt-mark", "showhold"],
            stdout = subprocess.PIPE, # subprocess.PIPE & subprocess.PIPE are alias of 'capture_output = True'
            stderr = subprocess.PIPE,
            universal_newlines = True # Alias of 'text = True'
        )

        if result.returncode != 0:
            raise Exception('could not get excluded (holded) packages list:' + result.stderr)

        return result.stdout.splitlines()


    #-----------------------------------------------------------------------------------------------
    #
    #   Exclude (hold) specified package
    #
    #-----------------------------------------------------------------------------------------------
    def exclude(self, package):
        result = subprocess.run(
            ["apt-mark", "hold", package],
            stdout = subprocess.PIPE, # subprocess.PIPE & subprocess.PIPE are alias of 'capture_output = True'
            stderr = subprocess.PIPE,
            universal_newlines = True # Alias of 'text = True'
        )

        if result.returncode != 0:
            raise Exception('could not exclude ' + package + ' package from update: ' + result.stderr)
        
    
    #-----------------------------------------------------------------------------------------------
    #
    #   Remove all package exclusions (unhold)
    #
    #-----------------------------------------------------------------------------------------------
    def remove_all_exclusions(self):
        # Retrieve the list of packages on hold
        list = self.get_exclusion()

        # Quit if there are no packages on hold
        if list == '':
            return

        # Unhold all packages
        for package in list:
            result = subprocess.run(
                ["apt-mark", "unhold", package],
                stdout = subprocess.PIPE, # subprocess.PIPE & subprocess.PIPE are alias of 'capture_output = True'
                stderr = subprocess.PIPE,
                universal_newlines = True # Alias of 'text = True'
            )

            if result.returncode != 0:
                raise Exception('could not unhold packages: ' + package)


    #-----------------------------------------------------------------------------------------------
    #
    #   Update packages
    #
    #-----------------------------------------------------------------------------------------------
    def update(self, packagesList, exit_on_package_update_error: bool = True, dry_run: bool = False):
        # Log file to store each package update output
        log = '/tmp/linupdate-update-package.log'

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

        # Loop through the list of packages to update
        for pkg in packagesList:
            # If the package is excluded, ignore it
            if pkg['excluded']:
                continue

            # If log file exists, remove it
            if Path(log).is_file():
                Path(log).unlink()

            with Log(log):
                print('\n ▪ Updating ' + Fore.GREEN + pkg['name'] + Style.RESET_ALL + ' (' + pkg['current_version'] + ' → ' + pkg['target_version'] + '):')

                # Before updating, check If package is already in the latest version, if so, skip it
                # It means that it has been updated previously by another package, probably because it was a dependency
                # Get the current version of the package from apt cache. Use a new temporary apt cache to be sure it is up to date
                try:
                    temp_apt_cache = apt.Cache()
                    temp_apt_cache.open(None)

                    # If version in cache is the same the target version, skip the update
                    if temp_apt_cache[pkg['name']].installed.version == pkg['target_version']:
                        print(Fore.GREEN + ' ✔ ' + Style.RESET_ALL + pkg['name'] + ' is already up to date (updated with another package).')

                        # Mark the package as already updated
                        self.summary['update']['success']['count'] += 1

                        # Also add the package to the list of successful packages
                        self.summary['update']['success']['packages'][pkg['name']] = {
                            'version': pkg['target_version'],
                            'log': 'Already up to date (updated with another package).'
                        }

                        # Continue to the next package
                        continue

                except Exception as e:
                    raise Exception('Could not retrieve current version of package ' + pkg['name'] + ': ' + str(e))

                # Define the command to update the package
                cmd = 'DEBIAN_FRONTEND=noninteractive /usr/bin/apt-get install ' + pkg['name'] + '=' + pkg['target_version'] +  ' -y'

                # If --keep-oldconf is True, then keep the old configuration files
                if self.keep_oldconf:
                    cmd += ' -o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold'

                # If --dry-run is True, then simulate the update
                if dry_run == True:
                    cmd += ' --dry-run'

                popen = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    shell = True
                )

                # Print lines as they are read
                for line in popen.stdout:
                    # Deal with carriage return
                    parts = line.split('\r')
                    for part in parts[:-1]:
                        sys.stdout.write('\r' + ' | ' + part.strip() + '\n')
                        sys.stdout.flush()
                    buffer = parts[-1]
                    sys.stdout.write('\r' + ' | ' + buffer.strip() + '\n')
                    sys.stdout.flush()

                # Deal with the carriage return of the last line
                sys.stdout.write('\r')
            
                # Wait for the command to finish
                popen.wait()

                # Get log content
                with open(log, 'r') as file:
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
                    if (exit_on_package_update_error == True):
                        raise Exception('Error while updating ' + pkg['name'] + '.')

                    # Else print an error message and continue to the next package
                    else:
                        print(Fore.RED + ' ✕ ' + Style.RESET_ALL + 'Error while updating ' + pkg['name'] + '.')
                        continue

                # Close the pipe
                popen.stdout.close()

                # If command succeeded, increment the success counter
                self.summary['update']['success']['count'] += 1

                # Add the package to the list of successful packages
                self.summary['update']['success']['packages'][pkg['name']] = {
                    'version': pkg['target_version'],
                    'log': log_content
                }

                # Print a success message
                print(Fore.GREEN + ' ✔ ' + Style.RESET_ALL + pkg['name'] + ' updated successfully.')


    #-----------------------------------------------------------------------------------------------
    #
    #   Return apt history log files sorted by modification time
    #
    #-----------------------------------------------------------------------------------------------
    def get_history(self, order):
        try:
            files = sorted(glob.glob('/var/log/apt/history.log*'), key=os.path.getmtime)

            # If order is newest, then sort by date in ascending order
            if order == 'newest':
                files.reverse()
        except Exception as e:
            raise Exception('could not get apt history log files: ' + str(e))

        return files


    #-----------------------------------------------------------------------------------------------
    #
    #   Parse all apt history log files and return a list of events (JSON)
    #
    #-----------------------------------------------------------------------------------------------
    def parse_history(self, history_files: list, entries_limit: int):
        # Initialize a limit counter which will be incremented until it reaches the entries_limit
        limit_counter = 0

        # Initialize a list of events
        events = []

        # Parse each apt history files
        for history_file in history_files:
            # If file is empty (e.g. file has been rotated), ignore it
            if os.stat(history_file).st_size == 0:
                continue

            # Retrieve all Start-Date in the history file
            result = subprocess.run(
                ['zgrep "^Start-Date:*" ' + history_file],
                stdout = subprocess.PIPE, # subprocess.PIPE & subprocess.PIPE are alias of 'capture_output = True'
                stderr = subprocess.PIPE,
                universal_newlines = True, # Alias of 'text = True'
                shell = True
            )

            # Quit if an error occurred
            if result.returncode != 0:
                raise Exception('no result matching the pattern "Start-Date" in file ' + history_file)

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
                if limit_counter > entries_limit:
                    break

                # Retrieve the event block : from the start date (START_DATE) to the next empty line
                # If the file is compressed, we must use zcat to read it
                if history_file.endswith('.gz'):
                    result = subprocess.run(
                        ['zcat ' + history_file + ' | sed -n "/' + start_date + '/,/^$/p"'],
                        stdout = subprocess.PIPE, # subprocess.PIPE & subprocess.PIPE are alias of 'capture_output = True'
                        stderr = subprocess.PIPE,
                        universal_newlines = True, # Alias of 'text = True'
                        shell = True
                    )

                # If the file is not compressed, we can use sed directly
                else:
                    result = subprocess.run(
                        ['sed -n "/' + start_date + '/,/^$/p" ' + history_file],
                        stdout = subprocess.PIPE, # subprocess.PIPE & subprocess.PIPE are alias of 'capture_output = True'
                        stderr = subprocess.PIPE,
                        universal_newlines = True, # Alias of 'text = True'
                        shell = True
                    )

                if result.returncode != 0:
                    raise Exception('no event found for date "' + start_date + '" in file ' + history_file)

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

        return events


    #-----------------------------------------------------------------------------------------------
    #
    #   Parse a string of one or multiple package(s) into a list of JSON objects
    #
    #-----------------------------------------------------------------------------------------------
    def parse_packages_line_to_json(self, packages: str, action: str):
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
            if action == 'install' or action == 'remove' or action == 'purge' or action == 'reinstall':
                version = package.split(' ')[1]
            if action == 'upgrade' or action == 'downgrade':
                version = package.split(' ')[2]

            # Remove parenthesis, commas, colons and spaces from name and version
            for char in ['(', ')', ',', ' ']:
                name = name.replace(char, '')
                version = version.replace(char, '')

            # Also remove architecture from name
            for arch in [':amd64', ':i386', ':all', ':arm64', ':armhf', ':armel', ':ppc64el', ':s390x', ':mips', ':mips64el', ':mipsel', ':powerpc', ':powerpcspe', ':riscv64', ':s390', ':sparc', ':sparc64']:
                if arch in name:
                    name = name.replace(arch, '')
        
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

        # Return the list of packages as JSON
        return packages_json
