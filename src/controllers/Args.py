# coding: utf-8

# Import libraries
from tabulate import tabulate
from colorama import Fore, Style
import sys
import argparse

# Import classes
from src.controllers.App.App import App
from src.controllers.App.Config import Config
from src.controllers.Module.Module import Module
from src.controllers.Exit import Exit

class Args:

    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Pre-parse arguments
    #
    #-------------------------------------------------------------------------------------------------------------------
    def pre_parse(self):
        # Default values
        Args.from_agent = False

        #
        # If --from-agent param has been set
        #
        if '--from-agent' in sys.argv:
            Args.from_agent = True


    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Parse arguments
    #
    #-------------------------------------------------------------------------------------------------------------------
    def parse(self):
        # Default values
        Args.assume_yes = False
        Args.check_updates = False
        Args.ignore_exclude = False
        Args.dist_upgrade = False
        Args.keep_oldconf = True

        myApp       = App()
        myAppConfig = Config()
        myModule    = Module()
        myExit      = Exit()

        try:
            # Parse arguments
            parser = argparse.ArgumentParser(add_help=False)

            # Define valid arguments
            # Help
            parser.add_argument("--help", "-h", action="store_true", default="null")
            # Version
            parser.add_argument("--version", "-v", action="store_true", default="null")

            # Profile
            parser.add_argument("--profile", "-p", action="store", nargs='?', default="null")
            # Environment
            parser.add_argument("--env", "-e", action="store", nargs='?', default="null")
            # Mail alert enable
            parser.add_argument("--mail-enable", action="store", nargs='?', default="null")
            # Get mail recipient
            parser.add_argument("--get-mail-recipient", action="store_true", default="null")
            # Set mail recipient
            parser.add_argument("--set-mail-recipient", action="store", nargs='?', default="null")
            
            # Dist upgrade
            parser.add_argument("--dist-upgrade", "-du", action="store_true", default="null")
            # Keep oldconf
            parser.add_argument("--keep-oldconf", action="store_true", default="null")
            # Force / assume-yes
            parser.add_argument("--assume-yes", "-y", action="store_true", default="null")
            # Check updates
            parser.add_argument("--check-updates", "-cu", action="store_true", default="null")
            # Ignore exclude
            parser.add_argument("--ignore-exclude", "-ie", action="store_true", default="null")

            # Get excluded packages
            parser.add_argument("--get-exclude", action="store", nargs='?', default="null")
            # Get excluded packages on major update
            parser.add_argument("--get-exclude-major", action="store", nargs='?', default="null")
            # Get services to restart after package update
            parser.add_argument("--get-service-restart", action="store", nargs='?', default="null")
            # Exclude
            parser.add_argument("--exclude", action="store", nargs='?', default="null")
            # Exclude on major update
            parser.add_argument("--exclude-major", action="store", nargs='?', default="null")
            # Services to restart after package update
            parser.add_argument("--service-restart", action="store", nargs='?', default="null")

            # List modules
            parser.add_argument("--mod-list", action="store_true", default="null")
            # Module enable
            parser.add_argument("--mod-enable", action="store", nargs='?', default="null")
            # Module disable
            parser.add_argument("--mod-disable", action="store", nargs='?', default="null")

            # Parse arguments
            args, remaining_args = parser.parse_known_args()

            # If remaining_args arguments are passed
            if remaining_args:
                # If --mod-configure is passed
                if '--mod-configure' in remaining_args:
                    # Retrieve all arguments after --mod-configure
                    mod_index = remaining_args.index('--mod-configure')
                    mod_args = remaining_args[mod_index + 1:]

                    # If no arguments are passed after --mod-configure, print an error
                    if not mod_args:
                        raise Exception('--mod-configure requires additional arguments')

                    # Else, pass the arguments to the module
                    else:
                        # Retrieve module name 
                        mod_name = mod_args[0]

                        # Retrieve all arguments after the module name
                        mod_args = mod_args[1:]

                        # Check if module exists
                        if not myModule.exists(mod_name):
                            raise Exception('Module ' + mod_name + ' does not exist')
                        
                        # Configure module
                        try:
                            myModule.configure(mod_name, mod_args)
                            myExit.clean_exit()
                        except Exception as e:
                            raise Exception('Could not configure ' + mod_name + ' module: ' + str(e))
                else:
                    raise Exception('Unknown argument(s): ' + str(remaining_args))

        except Exception as e:
            raise Exception(str(e))

        try:
            #
            # If --help param has been set
            #
            if args.help != "null":
                if args.help:
                    self.help()
                    myExit.clean_exit(0, False)

            #
            # If --version param has been set
            #
            if args.version != "null":
                if args.version:
                    print(' Current version: ' + myApp.get_version())
                    myExit.clean_exit(0, False)

            #
            # If --profile param has been set
            #
            if args.profile != "null":
                try:
                    # If a profile is set (not 'None'), change the app profile
                    if args.profile:
                        # Get current profile
                        currentProfile = myAppConfig.get_profile()

                        # If a profile was already set
                        if currentProfile:
                            # Print profile change
                            print(' Switching from profile ' + Fore.YELLOW + currentProfile + Style.RESET_ALL + ' to ' + Fore.YELLOW + args.profile + Style.RESET_ALL)
                        else:
                            # Print profile change
                            print(' Switching to profile ' + Fore.YELLOW + args.profile + Style.RESET_ALL)

                        # Set new profile
                        myAppConfig.set_profile(args.profile)

                    # Else print the current profile
                    else:
                        print(' Current profile: ' + Fore.YELLOW + myAppConfig.get_profile() + Style.RESET_ALL)
                    
                    myExit.clean_exit(0, False)

                except Exception as e:
                    raise Exception('could not switch profile: ' + str(e))

            #
            # If --env param has been set
            #
            if args.env != "null":
                try:
                    # If a environment is set (not 'None'), change the app environment
                    if args.env:
                        # Get current environment
                        currentEnvironment = myAppConfig.get_environment()

                        # Print environment change
                        print(' Switching from environment ' + Fore.YELLOW + currentEnvironment + Style.RESET_ALL + ' to ' + Fore.YELLOW + args.env + Style.RESET_ALL)

                        # Set new environment
                        myAppConfig.set_environment(args.env)
                    # Else print the current environment
                    else:
                        print(' Current environment: ' + Fore.YELLOW + myAppConfig.get_environment() + Style.RESET_ALL)

                    myExit.clean_exit(0, False)

                except Exception as e:
                    raise Exception('could not switch environment: ' + str(e))

            #
            # If --mail-enable param has been set
            #
            if args.mail_enable != "null":
                try:
                    if args.mail_enable == 'true':
                        myAppConfig.set_mail_enable(True)
                        print(' Mail sending ' + Fore.GREEN + 'enabled' + Style.RESET_ALL)
                    else:
                        myAppConfig.set_mail_enable(False)
                        print(' Mail sending ' + Fore.YELLOW  + 'disabled' + Style.RESET_ALL)

                    myExit.clean_exit(0, False)
                except Exception as e:
                    raise Exception('Could not configure mail: ' + str(e))

            #
            # If --get-mail-recipient param has been set
            #
            if args.get_mail_recipient != "null":
                try:
                    print(' Current mail recipient(s): ' + Fore.YELLOW)

                    recipients = myAppConfig.get_mail_recipient()

                    for recipient in recipients:
                        print('  ▪ ' + recipient)

                    # If no service is set to restart
                    if not recipients:
                        print('  ▪ None')

                    print(Style.RESET_ALL)
                
                    myExit.clean_exit(0, False)
                except Exception as e:
                    raise Exception('Could not get mail recipient(s): ' + str(e))

            #
            # If --set-mail-recipient param has been set
            #
            if args.set_mail_recipient != "null":
                try:
                    myAppConfig.set_mail_recipient(args.set_mail_recipient)
                    print(' Mail recipient set to ' + Fore.YELLOW + args.set_mail_recipient + Style.RESET_ALL)
                    myExit.clean_exit(0, False)
                except Exception as e:
                    raise Exception('Could not set mail recipient(s): ' + str(e))

            #
            # If --ignore-exclude param has been set
            # TODO : arg to test
            if args.ignore_exclude != "null":
                Args.ignore_exclude = True

            #
            # If --check-updates param has been set
            #
            if args.check_updates != "null":
                Args.check_updates = True

            #
            # If --dist-upgrade param has been set
            #
            if args.dist_upgrade != "null":
                Args.dist_upgrade = True

            #
            # If --keep-oldconf param has been set
            #
            if args.keep_oldconf != "null":
                Args.keep_oldconf = True

            #
            # If --assume-yes param has been set
            #
            if args.assume_yes != "null":
                Args.assume_yes = True

            #
            # If --get-exclude param has been set
            #
            if args.get_exclude != "null":
                try:
                    packages = myAppConfig.get_exclude()

                    print(' Currently excluded packages: ' + Fore.YELLOW)

                    for package in packages:
                        print('  ▪ ' + package)
                    
                    # If no package is excluded
                    if not packages:
                        print('  ▪ None')

                    print(Style.RESET_ALL)

                    myExit.clean_exit(0, False)
                except Exception as e:
                    raise Exception('Could not get excluded packages: ' + str(e))

            #
            # If --get-exclude-major param has been set
            #
            if args.get_exclude_major != "null":
                try:
                    packages = myAppConfig.get_exclude_major()

                    print(' Currently excluded packages on major update: ' + Fore.YELLOW)

                    for package in packages:
                        print('  ▪ ' + package)

                    # If no package is excluded
                    if not packages:
                        print('  ▪ None')

                    print(Style.RESET_ALL)

                    myExit.clean_exit(0, False)
                except Exception as e:
                    raise Exception('Could not get excluded packages on major update: ' + str(e))

            #
            # If --get-service-restart param has been set
            #
            if args.get_service_restart != "null":
                try:
                    services = myAppConfig.get_service_to_restart()

                    print(' Services to restart after package update: ' + Fore.YELLOW)

                    for service in services:
                        print('  ▪ ' + service)

                    # If no service is set to restart
                    if not services:
                        print('  ▪ None')

                    print(Style.RESET_ALL)

                    myExit.clean_exit(0, False)
                except Exception as e:
                    raise Exception('Could not get services to restart: ' + str(e))

            #
            # If --exclude param has been set
            #
            if args.exclude != "null":
                try:
                    # Exclude packages
                    myAppConfig.set_exclude(args.exclude)

                    # Print excluded packages
                    packages = myAppConfig.get_exclude()

                    print(' Excluding packages: ' + Fore.YELLOW)
                    
                    for package in packages:
                        print('  ▪ ' + package)

                    # If no package is excluded
                    if not packages:
                        print('  ▪ None')

                    print(Style.RESET_ALL)

                    myExit.clean_exit(0, False)
                except Exception as e:
                    raise Exception('Could not exclude packages: ' + str(e))

            #
            # If --exclude-major param has been set
            #
            if args.exclude_major != "null":
                try:
                    # Exclude packages on major update
                    myAppConfig.set_exclude_major(args.exclude_major)

                    # Print excluded packages
                    packages = myAppConfig.get_exclude_major()

                    print(' Excluding packages on major update: ' + Fore.YELLOW)

                    for package in packages:
                        print('  ▪ ' + package)

                    # If no package is excluded
                    if not packages:
                        print('  ▪ None')

                    print(Style.RESET_ALL)

                    myExit.clean_exit(0, False)
                except Exception as e:
                    raise Exception('Could not exclude packages on major update: ' + str(e))

            #
            # If --service-restart param has been set
            #
            if args.service_restart != "null":
                try:
                    # Set services to restart after package update
                    myAppConfig.set_service_to_restart(args.service_restart)

                    # Print services to restart
                    services = myAppConfig.get_service_to_restart()

                    print(' Setting services to restart after package update: ' + Fore.YELLOW)

                    for service in services:
                        print('  ▪ ' + service)

                    # If no service is set to restart
                    if not services:
                        print('  ▪ None')

                    print(Style.RESET_ALL)

                    myExit.clean_exit(0, False)
                except Exception as e:
                    raise Exception('Could not set services to restart after package update: ' + str(e))
            
            #
            # If --mod-list param has been set
            #
            if args.mod_list != "null":
                myModule.list()
                myExit.clean_exit(0, False)

            #
            # If --mod-enable param has been set
            #
            if args.mod_enable != "null":
                # If module to enable is set (not 'None'), enable the module
                if args.mod_enable:
                    # Enable module
                    try:
                        myModule.enable(args.mod_enable)
                        myExit.clean_exit(0, False)
                    except Exception as e:
                        raise Exception('Could not enable module: ' + str(e))
                else:
                    raise Exception('Module name is required')

            #
            # If --mod-disable param has been set
            #
            if args.mod_disable != "null":
                # If module to disable is set (not 'None'), disable the module
                if args.mod_disable:
                    # Disable module
                    try:
                        myModule.disable(args.mod_disable)
                        myExit.clean_exit(0, False)
                    except Exception as e:
                        raise Exception('Could not disable module: ' + str(e))
                else:
                    raise Exception('Module name is required')

        except Exception as e:
            raise Exception(str(e))


    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Print help
    #
    #-------------------------------------------------------------------------------------------------------------------
    def help(self):
        table = []
        options = [
            {
                'args': [
                    '--help',
                    '-h'
                ],
                'description': 'Show help',
            },
            {
                'args': [
                    '--version',
                    '-v'
                ],
                'description': 'Show version',
            },
            {
                'args': [
                    '--profile',
                    '-p'
                ],
                'option': 'PROFILE',
                'description': 'Print current profile or set profile'
            },
            {
                'args': [
                    '--env',
                    '-e'
                ],
                'option': 'ENVIRONMENT',
                'description': 'Print current environment or set environment'
            },
            {
                'args': [
                    '--mail-enable'
                ],
                'option': 'true|false',
                'description': 'Enable or disable mail reports'
            },
            {
                'args': [
                    '--get-mail-recipient'
                ],
                'description': 'Get current mail recipient(s)'
            },
            {
                'args': [
                    '--set-mail-recipient'
                ],
                'option': 'EMAIL',
                'description': 'Set mail recipient(s) (separated by commas)'
            },
            {
                'args': [
                    '--dist-upgrade',
                    '-du'
                ],
                'description': 'Enable distribution upgrade when updating packages (Debian based OS only)'
            },
            {
                'args': [
                    '--keep-oldconf'
                ],
                'description': 'Keep old configuration files when updating packages (Debian based OS only)'
            },
            {
                'args': [
                    '--assume-yes',
                    '-y'
                ],
                'description': 'Answer yes to all questions'
            },
            {
                'args': [
                    '--check-updates',
                    '-cu'
                ],
                'description': 'Only check for updates and exit'
            },
            {
                'args': [
                    '--ignore-exclude',
                    '-ie'
                ],
                'description': 'Ignore all package exclusions'
            },
            {
                'args': [
                    '--get-exclude'
                ],
                'description': 'Get the list of packages to exclude from update'
            },
            {
                'args': [
                    '--get-exclude-major'
                ],
                'description': 'Get the list of packages to exclude from update (if package has a major version update)'
            },
            {
                'args': [
                    '--get-service-restart'
                ],
                'description': 'Get the list of services to restart after package update'
            },
            {
                'args': [
                    '--exclude'
                ],
                'option': 'PACKAGE',
                'description': 'Set packages to exclude from update (separated by commas)'
            },
            {
                'args': [
                    '--exclude-major'
                ],
                'option': 'PACKAGE',
                'description': 'Set packages to exclude from update (if package has a major version update) (separated by commas)'
            },
            {
                'args': [
                    '--service-restart'
                ],
                'option': 'SERVICE',
                'description': 'Set services to restart after package update (separated by commas)'
            },
            {
                'args': [
                    '--mod-list'
                ],
                'description': 'List available modules'
            },
            {
                'args': [
                    '--mod-enable'
                ],
                'option': 'MODULE',
                'description': 'Enable a module'
            },
            {
                'args': [
                    '--mod-disable'
                ],
                'option': 'MODULE',
                'description': 'Disable a module'
            },
        ]

        # Add options to table
        for option in options:
            if len(option['args']) > 1:
                args_str = ', '.join(option['args'])
            else:
                args_str = option['args'][0]

            if 'option' in option:
                args_str += Style.DIM + ' [' + option['option'] + ']' + Style.RESET_ALL

            table.append(['', args_str, option['description']])


        print(' Available options:', end='\n\n')

        # Print table
        print(tabulate(table, headers=["", "Name", "Description"], tablefmt="simple"), end='\n\n')

        print(' Usage: linupdate [OPTIONS]', end='\n\n')
