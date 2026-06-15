#!/usr/bin/python3
# coding: utf-8

# Import libraries
import socket
import signal
import traceback
import sys
from datetime import datetime
from rich.console import Console
from colorama import Fore, Style

# Import classes
from src.controllers.Logging import StreamToLogger
from src.controllers.App.App import App
from src.controllers.App.Config import Config
from src.controllers.Args import Args
from src.controllers.System import System
from src.controllers.Module.Module import Module
from src.controllers.Package.Package import Package
from src.controllers.Service.Service import Service
from src.controllers.Exit import Exit
from src.controllers.ArgsException import ArgsException
from src.controllers.Status import status_manager


#-----------------------------------------------------------------------------------------------
#
#   Main function
#
#-----------------------------------------------------------------------------------------------
def main():
    exit_code = 0
    send_mail = True
    reboot = False

    try:
        # Handle Ctrl+C (KeyboardInterrupt)
        signal.signal(signal.SIGINT, signal.default_int_handler)

        # Exit if the user is not root
        if not System().is_root():
            print(Fore.YELLOW + 'Must be executed as root' + Style.RESET_ALL)
            sys.exit(1)

        # Define logfile
        logfile = '/var/log/linupdate/' + datetime.now().strftime('%Y-%m-%d') + '_' + datetime.now().strftime('%Hh%Mm%Ss') + '_linupdate_' + socket.getfqdn() + '.log'

        # Instanciate classes
        my_exit       = Exit()
        my_app        = App()
        my_app_config = Config() # instanciate to generate and check config
        my_args       = Args()
        my_system     = System()
        my_module     = Module()
        my_package    = Package()
        my_service    = Service()

        # Use logging context manager to redirect stdout and stderr to log file
        with StreamToLogger(logfile):
            # Print Logo
            my_app.print_logo()

            # Check if the system is supported
            my_system.check()

            # Create lock file
            my_app.set_lock()

            # Create base directories
            my_app.initialize()

            # Parse arguments
            my_args.parse()

            # Print system & app summary
            my_app.print_summary()

            # Load modules
            my_module.load()

            # Execute pre-update modules functions
            my_module.pre()

            # Execute packages update
            my_package.update(my_args.packages_to_update,
                              my_args.assume_yes,
                              my_args.ignore_exclusions,
                              my_args.check_updates,
                              my_args.dist_upgrade,
                              my_args.keep_oldconf,
                              my_args.clear_cache,
                              my_args.dry_run)

            # Execute post-update modules functions
            my_module.post(my_package.summary)

            # Reload services
            my_service.reload(my_package.summary, my_args.dry_run)

            # Restart services
            my_service.restart(my_package.summary, my_args.dry_run)

            # Check if reboot is required
            if System().reboot_required():
                print(' ' + Fore.YELLOW + 'Reboot is required' + Style.RESET_ALL)
            
                # If auto reboot is enabled
                if my_args.reboot:
                    reboot = True

                    # Do not reboot on dry run
                    if my_args.dry_run:
                        reboot = False

                # Print a message if the system will reboot automatically
                if reboot:
                    print(' ' + Fore.YELLOW + 'System will reboot automatically' + Style.RESET_ALL)

    # If an ArgsException is raised, print the error message and do not send an email
    except ArgsException as e:
        send_mail = False
        exit_code = 1

        print('\n' + Fore.RED + ' ✕ ' + Style.RESET_ALL + str(e) + '\n')
        # If debug mode is enabled, print the stack trace
        if getattr(Args, 'debug', False):
            print('Stack trace:' + '\n' + traceback.format_exc())

    # If an exception is raised, print the error message and send an email
    except Exception as e:
        exit_code = 1

        print('\n' + Fore.RED + ' ✕ ' + Style.RESET_ALL + str(e) + '\n')
        # If debug mode is enabled, print the stack trace
        if getattr(Args, 'debug', False):
            print('Stack trace:' + '\n' + traceback.format_exc())

    # If the user presses Ctrl+C or the script is killed, do not send an email and exit with code 2
    except KeyboardInterrupt as e:
        send_mail = False
        exit_code = 2

    # Exit with exit code and logfile for email report
    my_exit.clean_exit(exit_code, send_mail, reboot, logfile)

# Run main function
console = Console(file=sys.__stdout__)

# Create status and register it with StatusManager
rich_status = console.status("Running...")
status_manager.set_status(rich_status)

with rich_status:
    main()

# Clear status when done
status_manager.clear()
