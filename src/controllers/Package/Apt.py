# coding: utf-8

# Import libraries
import apt
import subprocess
import glob
import os
import re
from colorama import Fore, Style

class Apt:
    def __init__(self):
        # Create an instance of the apt cache
        self.aptcache = apt.Cache()

        # self.aptcache.update()
        self.aptcache.open(None)

        # Total count of success and failed package updates
        self.summary = {
            'update': {
                'success': {
                    'count': 0,
                    'packages': []
                },
                'failed': {
                    'count': 0,
                    'packages': []
                }
            }
        }

        # Define some default options
        self.dist_upgrade = False
        self.keep_oldconf = True


    #-----------------------------------------------------------------------------------------------
    #
    #   Return list of installed apt packages, sorted by name
    #
    #-----------------------------------------------------------------------------------------------
    def get_installed_packages(self):
        list = []

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
    def get_available_packages(self):
        try:
            list = []

            # Simulate an upgrade
            self.aptcache.upgrade()

            # Loop through all packages marked for upgrade
            for pkg in self.aptcache.get_changes():
                # If the package is upgradable, add it to the list of available packages
                if pkg.is_upgradable:
                    myPackage = {
                        'name': pkg.name,
                        'current_version': pkg.installed.version,
                        'available_version': pkg.candidate.version
                    }

                    list.append(myPackage)
            
            # Sort the list by package name
            list.sort(key=lambda x: x['name'])

        except Exception as e:
            raise Exception('could not get available packages: ' + str(e))
        
        return list


    #-----------------------------------------------------------------------------------------------
    #
    #   Clear apt cache
    #
    #-----------------------------------------------------------------------------------------------
    def clear_cache(self):
        result = subprocess.run(
            ["apt", "clean", "all"],
            stdout = subprocess.PIPE, # subprocess.PIPE & subprocess.PIPE are alias of 'capture_output = True'
            stderr = subprocess.PIPE,
            universal_newlines = True # Alias of 'text = True'
        )

        if result.returncode != 0:
            raise Exception('could not clear apt cache: ' + result.stderr)


    #-----------------------------------------------------------------------------------------------
    #
    #   Update apt cache
    #
    #-----------------------------------------------------------------------------------------------
    def update_cache(self):
        try:
            self.aptcache.upgrade()

        except Exception as e:
            raise Exception('could not update apt cache: ' + str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   Get list of excluded packages (hold)
    #
    #-----------------------------------------------------------------------------------------------
    def get_exclude(self):
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
        list = self.get_exclude()

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
    def update(self, packagesList, update_method: str = 'one_by_one', exit_on_package_update_error: bool = True):
        # If update_method is 'one_by_one', update packages one by one (one command per package)
        if update_method == 'one_by_one':
            # Loop through the list of packages to update
            for pkg in packagesList:
                # If the package is excluded, ignore it
                if pkg['excluded']:
                    continue

                print('\n ▪ Updating ' + Fore.GREEN + pkg['name'] + Style.RESET_ALL + ' (' + pkg['current_version'] + ' → ' + pkg['available_version'] + '):')

                # If --keep-oldconf is True, then keep the old configuration file
                if self.keep_oldconf:
                    cmd = ['apt-get', 'install', pkg['name'], '-y', '-o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"']
                else:
                    cmd = ['apt-get', 'install', pkg['name'], '-y']

                # popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1, universal_newlines=True)
                popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

                # TODO : une fois la solution trouvée, la reporter plus bas
                # Print lines as they are read
                for line in popen.stdout:
                    line = line.replace('\r', '')
                    print(' | ' + line.strip(), end='')               

                # Wait for the command to finish
                popen.wait()

                # If command failed, either raise an exception or print a warning
                if popen.returncode != 0:

                    self.summary['update']['failed']['count'] += 1

                    # If error is critical, raise an exception
                    if (exit_on_package_update_error == True):
                        raise Exception('error while updating ' + pkg['name'])

                    # Else print a warning and continue to the next package
                    else:
                        print('error while updating ' + pkg['name'])
                        continue

                # Close the pipe
                popen.stdout.close()

                # If command succeeded, increment the success counter
                self.summary['update']['success']['count'] += 1

        # TODO : à tester
        # If update_method is 'global', update all packages at once (one command)
        if update_method == 'global':
            # If --keep-oldconf is True, then keep the old configuration file
            if self.keep_oldconf:
                cmd = ['apt-get', 'upgrade', '-y', '-o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"']
            else:
                cmd = ['apt-get', 'upgrade', '-y']

            popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1, universal_newlines=True)

            # Print lines as they are read
            for line in popen.stdout:
                line = line.replace('\r', '')
                print(' | ' + line, end='')

            # Wait for the command to finish
            popen.wait()

            # If command failed, either raise an exception or print a warning
            if popen.returncode != 0:
                # If error is critical, raise an exception
                if (exit_on_package_update_error == True):
                    raise Exception('error while updating packages')

            # Close the pipe
            popen.stdout.close()


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
                raise Exception('could not retrieve Start-Date from ' + history_file + ': ' + result.stderr)

            # Split the result into a list
            start_dates = result.stdout.strip().split('\n')

            # TODO : peut être pas utile finalement
            # ignore_start_date = ''

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

                # Ignore this entry if it has the same Start-Date as the previous one
                # TODO : peut être pas utile finalement
                # if start_date == ignore_start_date:
                #     continue

                # TODO : peut être pas utile finalement
                # Before starting to parse, we check if there were not multiple events at the same date in the history file
                # result = subprocess.run(
                #     ['zgrep "' + start_date + '" ' + history_file + ' | wc -l'],
                #     stdout = subprocess.PIPE, # subprocess.PIPE & subprocess.PIPE are alias of 'capture_output = True'
                #     stderr = subprocess.PIPE,
                #     universal_newlines = True # Alias of 'text = True'
                #     shell = True
                # )

                # if result.returncode != 0:
                #     raise Exception('could not count events for ' + start_date + ' in ' + history_file + ': ' + result.stderr)
                
                # count_event = int(result.stdout.strip())
                # TODO : on met en dur car peut être pas utile finalement
                count_event = 1

                # If there is only one event, we can parse it
                if count_event == 1:
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
                        raise Exception('could not retrieve event for ' + start_date + ' in ' + history_file + ': ' + result.stderr)

                    # Retrieve event block lines
                    event = result.stdout.strip()

                    # From the retrieved event block, we can get the start date and time and the end date and time
                    date_start = re.search(r'^Start-Date: (.+)', event).group(1).split()[0].strip()
                    time_start = re.search(r'^Start-Date: (.+)', event).group(1).split()[1].strip()
                    date_end = re.search(r'End-Date: (.+)', event).group(1).split()[0].strip()
                    time_end = re.search(r'End-Date: (.+)', event).group(1).split()[1].strip()

                    # Retrieve the event command
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
   
                # TODO : peut être pas utile finalement
                # if count_event > 1:
                #     temporary_file = '/tmp/apt_history_temporary_file'

                    # Retrieve all events with the same date into a signle temporary file



                    # Finally, since we have processed multiple same events from the log file, we ignore all the next events that would be at the same date (so that they are not processed twice)
                    # ignore_start_date = start_date


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
        
            # Add the package to the list of packages
            packages_json.append({
                'name': name,
                'version': version
            })

        # Return the list of packages as JSON
        return packages_json
