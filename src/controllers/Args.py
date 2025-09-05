# coding: utf-8

# Import libraries
import sys
import argparse
from tabulate import tabulate
from colorama import Fore, Style

# Import classes
from src.controllers.App.App import App
from src.controllers.App.Config import Config
from src.controllers.Module.Module import Module
from src.controllers.Exit import Exit
from src.controllers.ArgsException import ArgsException
from src.controllers.App.Service import Service as AppService

class Args:
    #-----------------------------------------------------------------------------------------------
    #
    #   Parse arguments
    #
    #-----------------------------------------------------------------------------------------------
    def parse(self):
        # Default values
        Args.assume_yes = False
        Args.check_updates = False
        Args.ignore_exclusions = False
        Args.packages_to_update = []
        Args.dist_upgrade = False
        Args.keep_oldconf = True
        Args.dry_run = False
        Args.debug = False

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
            # Debug
            parser.add_argument("--debug", action="store_true", default="null")
            # Show raw config
            parser.add_argument("--show-config", "-sc", action="store_true", default="null")

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
            # Get mail smtp host
            parser.add_argument("--get-mail-smtp-host", action="store_true", default="null")
            # Set mail smtp host
            parser.add_argument("--set-mail-smtp-host", action="store", nargs='?', default="null")
            # Get mail smtp port
            parser.add_argument("--get-mail-smtp-port", action="store_true", default="null")
            # Set mail smtp port
            parser.add_argument("--set-mail-smtp-port", action="store", nargs='?', default="null")

            # Packages to update list
            parser.add_argument("--update", "-u", action="store", nargs='?', default="null")
            # Dist upgrade
            parser.add_argument("--dist-upgrade", "-du", action="store_true", default="null")
            # Dry run
            parser.add_argument("--dry-run", action="store_true", default="null")
            # Keep oldconf
            parser.add_argument("--keep-oldconf", action="store_true", default="null")
            # Force / assume-yes
            parser.add_argument("--assume-yes", "-y", action="store_true", default="null")
            # Check updates
            parser.add_argument("--check-updates", "-cu", action="store_true", default="null")
            # Ignore exclude
            parser.add_argument("--ignore-exclusions", "-ie", action="store_true", default="null")
            # Exit on package update error
            parser.add_argument("--exit-on-package-update-error", action="store", nargs='?', default="null")

            # Get excluded packages
            parser.add_argument("--get-exclude", action="store", nargs='?', default="null")
            # Get excluded packages on major update
            parser.add_argument("--get-exclude-major", action="store", nargs='?', default="null")
            # Get services to reload after package update
            parser.add_argument("--get-service-reload", action="store", nargs='?', default="null")
            # Get services to restart after package update
            parser.add_argument("--get-service-restart", action="store", nargs='?', default="null")
            # Exclude
            parser.add_argument("--exclude", action="store", nargs='?', default="null")
            # Exclude on major update
            parser.add_argument("--exclude-major", action="store", nargs='?', default="null")
            # Get services to reload after package update
            parser.add_argument("--service-reload", action="store", nargs='?', default="null")
            # Services to restart after package update
            parser.add_argument("--service-restart", action="store", nargs='?', default="null")

            # List modules
            parser.add_argument("--mod-list", action="store_true", default="null")
            # Module enable
            parser.add_argument("--mod-enable", action="store", nargs='?', default="null")
            # Module disable
            parser.add_argument("--mod-disable", action="store", nargs='?', default="null")

            # Service tuning
            parser.add_argument("--cpu-priority", action="store", nargs='?', default="null")
            parser.add_argument("--memory-limit", action="store", nargs='?', default="null")
            parser.add_argument("--oom-score", action="store", nargs='?', default="null")

            # Parse arguments
            args, remaining_args = parser.parse_known_args()

            # If remaining_args arguments are passed
            if remaining_args:
                # If --mod-configure or -mc or --mod-exec or -me is in list (use regex)
                if '--mod-configure' in remaining_args or '-mc' in remaining_args or '--mod-exec' in remaining_args or '-me' in remaining_args:
                    if '--mod-configure' in remaining_args:
                        param_name = '--mod-configure'
                    elif '-mc' in remaining_args:
                        param_name = '-mc'
                    elif '--mod-exec' in remaining_args:
                        param_name = '--mod-exec'
                    elif '-me' in remaining_args:
                        param_name = '-me'

                    # Retrieve all arguments after --mod-configure (or -mc, etc.)
                    mod_index = remaining_args.index(param_name)
                    mod_args = remaining_args[mod_index + 1:]

                    # If no arguments are passed after --mod-configure, print an error
                    if not mod_args:
                        raise ArgsException(param_name + ' requires additional arguments')

                    # Else, pass the arguments to the module
                    else:
                        # Retrieve module name
                        mod_name = mod_args[0]

                        # Retrieve all arguments after the module name
                        mod_args = mod_args[1:]

                        # Check if module exists
                        if not myModule.exists(mod_name):
                            raise ArgsException('Module ' + mod_name + ' does not exist')

                        # Configure module
                        try:
                            myModule.configure(mod_name, mod_args)
                            myExit.clean_exit(0, False)
                        except Exception as e:
                            raise ArgsException('Could not configure ' + mod_name + ' module: ' + str(e))

                # If there are remaining arguments, print help and raise an exception
                else:
                    self.help()
                    raise ArgsException('Unknown argument(s): ' + str(remaining_args))

        # Catch exceptions
        # Either ArgsException or Exception, it will always raise an ArgsException to the main script, this to avoid sending an email when an argument error occurs
        except (ArgsException, Exception) as e:
            raise ArgsException(str(e))

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
                    print(' Current version: ' + Fore.GREEN + myApp.get_version() + Style.RESET_ALL, end='\n\n')
                    myExit.clean_exit(0, False)

            #
            # If --debug param has been set
            #
            if args.debug != "null":
                if args.debug:
                    Args.debug = True

            #
            # If --show-config param has been set
            #
            if args.show_config != "null":
                if args.show_config:
                    myAppConfig.show_config()
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

                        # Print profile change
                        print(' Switching from profile ' + Fore.GREEN + currentProfile + Style.RESET_ALL + ' to ' + Fore.GREEN + args.profile + Style.RESET_ALL, end='\n\n')

                        # Set new profile
                        myAppConfig.set_profile(args.profile)

                    # Else print the current profile
                    else:
                        print(' Current profile: ' + Fore.GREEN + myAppConfig.get_profile() + Style.RESET_ALL, end='\n\n')

                    myExit.clean_exit(0, False)

                except Exception as e:
                    raise ArgsException('could not switch profile: ' + str(e))

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
                        print(' Switching from environment ' + Fore.GREEN + currentEnvironment + Style.RESET_ALL + ' to ' + Fore.GREEN + args.env + Style.RESET_ALL, end='\n\n')

                        # Set new environment
                        myAppConfig.set_environment(args.env)
                    # Else print the current environment
                    else:
                        print(' Current environment: ' + Fore.GREEN + myAppConfig.get_environment() + Style.RESET_ALL, end='\n\n')

                    myExit.clean_exit(0, False)

                except Exception as e:
                    raise ArgsException('could not switch environment: ' + str(e))

            #
            # If --mail-enable param has been set
            #
            if args.mail_enable != "null":
                try:
                    if args.mail_enable == 'true':
                        myAppConfig.set_mail_enable(True)
                        print(' Mail sending ' + Fore.GREEN + 'enabled' + Style.RESET_ALL, end='\n\n')
                    else:
                        myAppConfig.set_mail_enable(False)
                        print(' Mail sending ' + Fore.YELLOW  + 'disabled' + Style.RESET_ALL, end='\n\n')

                    myExit.clean_exit(0, False)
                except Exception as e:
                    raise ArgsException('Could not configure mail: ' + str(e))

            #
            # If --get-mail-recipient param has been set
            #
            if args.get_mail_recipient != "null":
                try:
                    print(' Current mail recipient(s): ' + Fore.GREEN)

                    recipients = myAppConfig.get_mail_recipient()

                    # If no recipient is set
                    if not recipients:
                        print('  ▪ None')
                    else:
                        for recipient in recipients:
                            print('  ▪ ' + recipient)

                    print(Style.RESET_ALL, end='\n')

                    myExit.clean_exit(0, False)
                except Exception as e:
                    raise ArgsException('Could not get mail recipient(s): ' + str(e))

            #
            # If --set-mail-recipient param has been set
            #
            if args.set_mail_recipient != "null":
                try:
                    myAppConfig.set_mail_recipient(args.set_mail_recipient)

                    print(' Mail recipient set to:' + Fore.GREEN)

                    # If no recipient is set
                    if not args.set_mail_recipient:
                        print('  ▪ None')
                    else:
                        for item in args.set_mail_recipient.split(","):
                            print('  ▪ ' + item)

                    print(Style.RESET_ALL, end='\n')

                    myExit.clean_exit(0, False)
                except Exception as e:
                    raise ArgsException('Could not set mail recipient(s): ' + str(e))

            #
            # If --get-mail-smtp-host param has been set
            #
            if args.get_mail_smtp_host != "null":
                try:
                    print(' Current mail SMTP host: ' + Fore.GREEN + myAppConfig.get_mail_smtp_host() + Style.RESET_ALL, end='\n\n')
                    myExit.clean_exit(0, False)
                except Exception as e:
                    raise ArgsException('Could not get mail SMTP host: ' + str(e))

            #
            # If --set-mail-smtp-host param has been set
            #
            if args.set_mail_smtp_host != "null":
                try:
                    myAppConfig.set_mail_smtp_host(args.set_mail_smtp_host)
                    print(' Mail SMTP host set to: ' + Fore.GREEN + args.set_mail_smtp_host + Style.RESET_ALL, end='\n\n')
                    myExit.clean_exit(0, False)
                except Exception as e:
                    raise ArgsException('Could not set mail SMTP host: ' + str(e))

            #
            # If --get-mail-smtp-port param has been set
            #
            if args.get_mail_smtp_port != "null":
                try:
                    print(' Current mail SMTP port: ' + Fore.GREEN + str(myAppConfig.get_mail_smtp_port()) + Style.RESET_ALL, end='\n\n')
                    myExit.clean_exit(0, False)
                except Exception as e:
                    raise ArgsException('Could not get mail SMTP port: ' + str(e))

            #
            # If --set-mail-smtp-port param has been set
            #
            if args.set_mail_smtp_port != "null":
                try:
                    myAppConfig.set_mail_smtp_port(args.set_mail_smtp_port)
                    print(' Mail SMTP port set to: ' + Fore.GREEN + str(args.set_mail_smtp_port) + Style.RESET_ALL, end='\n\n')
                    myExit.clean_exit(0, False)
                except Exception as e:
                    raise ArgsException('Could not set mail SMTP port: ' + str(e))

            #
            # If --update param has been set
            #
            if args.update != "null":
                if not args.update:
                    raise ArgsException('Package(s) name must be specified when using --update')

                try:
                    for package in args.update.split(','):
                        Args.packages_to_update.append({'name': package.strip()})
                except Exception as e:
                    raise ArgsException('Could not parse update list: ' + str(e))

            #
            # If --dry-run param has been set
            #
            if args.dry_run != "null":
                Args.dry_run = True

            #
            # If --ignore-exclusions param has been set
            #
            if args.ignore_exclusions != "null":
                Args.ignore_exclusions = True

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
            # If --exit-on-package-update-error param has been set
            #
            if args.exit_on_package_update_error != "null":
                try:
                    if args.exit_on_package_update_error == 'true':
                        myAppConfig.set_exit_on_package_update_error(True)
                        print(' Exit on package update error ' + Fore.GREEN + 'enabled' + Style.RESET_ALL, end='\n\n')
                    else:
                        myAppConfig.set_exit_on_package_update_error(False)
                        print(' Exit on package update error ' + Fore.YELLOW  + 'disabled' + Style.RESET_ALL, end='\n\n')

                    myExit.clean_exit(0, False)
                except Exception as e:
                    raise ArgsException('Could not configure exit on package update error: ' + str(e))

            #
            # If --get-exclude param has been set
            #
            if args.get_exclude != "null":
                try:
                    packages = myAppConfig.get_exclusion()

                    print(' Currently excluded packages: ' + Fore.GREEN)

                    # If no package is excluded
                    if not packages:
                        print('  ▪ None')
                    else:
                        for package in packages:
                            print('  ▪ ' + package)

                    print(Style.RESET_ALL)

                    myExit.clean_exit(0, False)
                except Exception as e:
                    raise ArgsException('Could not get excluded packages: ' + str(e))

            #
            # If --get-exclude-major param has been set
            #
            if args.get_exclude_major != "null":
                try:
                    packages = myAppConfig.get_major_exclusion()

                    print(' Currently excluded packages on major update: ' + Fore.GREEN)

                    # If no package is excluded
                    if not packages:
                        print('  ▪ None')
                    else:
                        for package in packages:
                            print('  ▪ ' + package)

                    print(Style.RESET_ALL)

                    myExit.clean_exit(0, False)
                except Exception as e:
                    raise ArgsException('Could not get excluded packages on major update: ' + str(e))

            #
            # If --get-service-reload param has been set
            #
            if args.get_service_reload != "null":
                try:
                    services = myAppConfig.get_service_to_reload()

                    print(' Services to reload after package update: ' + Fore.GREEN)

                    # If no service is set to reload
                    if not services:
                        print('  ▪ None')
                    else:
                        for service in services:
                            print('  ▪ ' + service)

                    print(Style.RESET_ALL, end='\n')

                    myExit.clean_exit(0, False)
                except Exception as e:
                    raise ArgsException('Could not get services to reload: ' + str(e))

            #
            # If --get-service-restart param has been set
            #
            if args.get_service_restart != "null":
                try:
                    services = myAppConfig.get_service_to_restart()

                    print(' Services to restart after package update: ' + Fore.GREEN)

                    # If no service is set to restart
                    if not services:
                        print('  ▪ None')
                    else:
                        for service in services:
                            print('  ▪ ' + service)

                    print(Style.RESET_ALL, end='\n')

                    myExit.clean_exit(0, False)
                except Exception as e:
                    raise ArgsException('Could not get services to restart: ' + str(e))

            #
            # If --exclude param has been set
            #
            if args.exclude != "null":
                try:
                    # Exclude packages
                    myAppConfig.set_exclusion(args.exclude)

                    # Print excluded packages
                    packages = myAppConfig.get_exclusion()

                    print(' Excluding packages: ' + Fore.GREEN)

                    # If no package is excluded
                    if not packages:
                        print('  ▪ None')
                    else:
                        for package in packages:
                            print('  ▪ ' + package)

                    print(Style.RESET_ALL)

                    myExit.clean_exit(0, False)
                except Exception as e:
                    raise ArgsException('Could not exclude packages: ' + str(e))

            #
            # If --exclude-major param has been set
            #
            if args.exclude_major != "null":
                try:
                    # Exclude packages on major update
                    myAppConfig.set_major_exclusion(args.exclude_major)

                    # Print excluded packages
                    packages = myAppConfig.get_major_exclusion()

                    print(' Excluding packages on major update: ' + Fore.GREEN)

                    # If no package is excluded
                    if not packages:
                        print('  ▪ None')
                    else:
                        for package in packages:
                            print('  ▪ ' + package)

                    print(Style.RESET_ALL)

                    myExit.clean_exit(0, False)
                except Exception as e:
                    raise ArgsException('Could not exclude packages on major update: ' + str(e))

            #
            # If --service-reload param has been set
            #
            if args.service_reload != "null":
                try:
                    # Set services to reload after package update
                    myAppConfig.set_service_to_reload(args.service_reload)

                    # Print services to reload
                    services = myAppConfig.get_service_to_reload()

                    print(' Setting services to reload after package update: ' + Fore.GREEN)

                    # If no service is set to reload
                    if not services:
                        print('  ▪ None')
                    else:
                        for service in services:
                            print('  ▪ ' + service)

                    print(Style.RESET_ALL)

                    myExit.clean_exit(0, False)
                except Exception as e:
                    raise ArgsException('Could not set services to reload after package update: ' + str(e))

            #
            # If --service-restart param has been set
            #
            if args.service_restart != "null":
                try:
                    # Set services to restart after package update
                    myAppConfig.set_service_to_restart(args.service_restart)

                    # Print services to restart
                    services = myAppConfig.get_service_to_restart()

                    print(' Setting services to restart after package update: ' + Fore.GREEN)

                    # If no service is set to restart
                    if not services:
                        print('  ▪ None')
                    else:
                        for service in services:
                            print('  ▪ ' + service)

                    print(Style.RESET_ALL)

                    myExit.clean_exit(0, False)
                except Exception as e:
                    raise ArgsException('Could not set services to restart after package update: ' + str(e))

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
                        raise ArgsException('Could not enable module: ' + str(e))
                else:
                    raise ArgsException('Module name is required')

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
                        raise ArgsException('Could not disable module: ' + str(e))
                else:
                    raise ArgsException('Module name is required')

            #
            # If --cpu-priority param has been set
            #
            if args.cpu_priority != "null":
                try:
                    # If no CPU priority is set, get the current CPU priority
                    if not args.cpu_priority:
                        print(' Current CPU priority is ' + Fore.GREEN + AppService().get_cpu_priority() + Style.RESET_ALL, end='\n\n')
                    else:
                        # Set CPU priority
                        AppService().set_cpu_priority(args.cpu_priority)
                        print(' CPU priority set to ' + Fore.GREEN + str(args.cpu_priority) + Style.RESET_ALL, end='\n\n')

                    myExit.clean_exit(0, False)
                except Exception as e:
                    raise ArgsException(str(e))

            #
            # If --memory-limit param has been set
            #
            if args.memory_limit != "null":
                try:
                    # If no memory limit is set, get the current memory limit
                    if not args.memory_limit:
                        print(' Current memory limit is ' + Fore.GREEN + AppService().get_memory_limit() + Style.RESET_ALL, end='\n\n')
                    else:
                        # Set memory limit
                        AppService().set_memory_limit(args.memory_limit)
                        print(' Memory limit set to ' + Fore.GREEN + str(args.memory_limit) + Style.RESET_ALL, end='\n\n')

                    myExit.clean_exit(0, False)
                except Exception as e:
                    raise ArgsException(str(e))

            #
            # If --oom-score param has been set
            #
            if args.oom_score != "null":
                try:
                    # If no OOM score is set, get the current OOM score
                    if not args.oom_score:
                        print(' Current OOM score is ' + Fore.GREEN + AppService().get_oom_score() + Style.RESET_ALL, end='\n\n')
                    else:
                        # Set OOM score
                        AppService().set_oom_score(args.oom_score)
                        print(' OOM score set to ' + Fore.GREEN + str(args.oom_score) + Style.RESET_ALL, end='\n\n')

                    myExit.clean_exit(0, False)
                except Exception as e:
                    raise ArgsException(str(e))

        # Catch exceptions
        # Either ArgsException or Exception, it will always raise an ArgsException to the main script, this to avoid sending an email when an argument error occurs
        except (ArgsException, Exception) as e:
            raise ArgsException(str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   Print help
    #
    #-----------------------------------------------------------------------------------------------
    def help(self):
        try:
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
                        '--show-config',
                        '-sc'
                    ],
                    'description': 'Show raw configuration',
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
                        '--debug'
                    ],
                    'description': 'Enable debug mode',
                },
                {
                    'title': 'Global configuration options'
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
                        '--get-mail-smtp-host'
                    ],
                    'description': 'Get current mail SMTP host'
                },
                {
                    'args': [
                        '--set-mail-smtp-host'
                    ],
                    'option': 'HOST',
                    'description': 'Set mail SMTP host'
                },
                {
                    'args': [
                        '--get-mail-smtp-port'
                    ],
                    'description': 'Get current mail SMTP port'
                },
                {
                    'args': [
                        '--set-mail-smtp-port'
                    ],
                    'option': 'PORT',
                    'description': 'Set mail SMTP port'
                },
                {
                    'title': 'Update options'
                },
                {
                    'args': [
                        '--update',
                        '-u'
                    ],
                    'option': 'PACKAGE',
                    'description': 'Update only the specified packages (separated by commas)'
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
                        '--dry-run'
                    ],
                    'description': 'Simulate the update process (do not update packages)'
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
                        '--ignore-exclusions',
                        '-ie'
                    ],
                    'description': 'Ignore all package exclusions'
                },
                {
                    'args': [
                        '--exit-on-package-update-error',
                    ],
                    'option': 'true|false',
                    'description': 'Immediately exit if an error occurs during package update and do not update the remaining packages'
                },
                {
                    'title': 'Packages exclusion and services restart'
                },
                {
                    'args': [
                        '--get-exclude'
                    ],
                    'description': 'Get the current list of packages to exclude from update'
                },
                {
                    'args': [
                        '--get-exclude-major'
                    ],
                    'description': 'Get the current list of packages to exclude from update (if package has a major version update)'
                },
                {
                    'args': [
                        '--get-service-reload'
                    ],
                    'description': 'Get the current list of services to reload after package update'
                },
                {
                    'args': [
                        '--get-service-restart'
                    ],
                    'description': 'Get the current list of services to restart after package update'
                },
                {
                    'args': [
                        '--exclude'
                    ],
                    'option': 'PACKAGE',
                    'description': 'Set packages to exclude from update (separated by commas). Regex pattern ".*" can be used to match multiple packages. Example: --exclude php.*'
                },
                {
                    'args': [
                        '--exclude-major'
                    ],
                    'option': 'PACKAGE',
                    'description': 'Set packages to exclude from update (if package has a major version update) (separated by commas). Regex pattern ".*" can be used to match multiple packages. Example: --exclude-major php.*'
                },
                {
                    'args': [
                        '--service-reload'
                    ],
                    'option': 'SERVICE',
                    'description': 'Set services to reload after package update (separated by commas)'
                },
                {
                    'args': [
                        '--service-restart'
                    ],
                    'option': 'SERVICE',
                    'description': 'Set services to restart after package update (separated by commas)'
                },
                {
                    'title': 'Modules'
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
                {
                    'title': 'Service tuning'
                },
                {
                    'args': [
                        '--cpu-priority'
                    ],
                    'option': 'high, medium, low',
                    'description': 'Set CPU priority profile for the linupdate service. Lower priority means less CPU usage but also more time to complete service operations - default is high'
                },
                {
                    'args': [
                        '--memory-limit'
                    ],
                    'option': 'bytes',
                    'description': 'Set memory limit for the linupdate service in bytes - default is 1G'
                },
                {
                    'args': [
                        '--oom-score'
                    ],
                    'option': '-1000 to 1000',
                    'description': 'Set OOM (Out Of Memory) score for the linupdate service - the higher the value, the more likely the service will be killed by the OOM killer - default is 500'
                },
            ]

            # Add options to table
            for option in options:
                # If option is a title, just print it
                if 'title' in option:
                    table.append(['', Style.BRIGHT + '\n' + option['title'] + '\n' + Style.RESET_ALL, ''])
                    continue

                # If option has multiple arguments, join them
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

            del table, options, args_str

        # Catch exceptions
        # Either ArgsException or Exception, it will always raise an ArgsException to the main script, this to avoid sending an email when an argument error occurs
        except (ArgsException, Exception) as e:
            raise ArgsException('Printing help error: ' + str(e))
