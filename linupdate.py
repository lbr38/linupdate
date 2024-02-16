#!/usr/bin/python3
# coding: utf-8

# Import libraries
import socket
from pathlib import Path
from datetime import datetime
from colorama import Fore, Style

# Import classes
from src.controllers.Log import Log
from src.controllers.App.App import App
from src.controllers.App.Config import Config
from src.controllers.Args import Args
from src.controllers.System import System
from src.controllers.Module.Module import Module
from src.controllers.Package.Package import Package
from src.controllers.Service.Service import Service
from src.controllers.Exit import Exit
from src.controllers.ArgsException import ArgsException

#-----------------------------------------------------------------------------------------------
#
#   Main function
#
#-----------------------------------------------------------------------------------------------
def main():
    exit_code = 0
    send_mail = True

    try:
        # Get current date and time
        todaydatetime = datetime.now()
        date = todaydatetime.strftime('%Y-%m-%d')
        time = todaydatetime.strftime('%Hh%Mm%Ss')
        logsdir = '/var/log/linupdate'
        logfile = date + '_' + time + '_linupdate_' + socket.gethostname() + '.log'

        # Create logs directory
        Path(logsdir).mkdir(parents=True, exist_ok=True)
        Path(logsdir).chmod(0o750)

        # Instanciate classes
        my_exit       = Exit()
        my_app        = App()
        my_app_config = Config()
        my_args       = Args()
        my_system     = System()
        my_module     = Module()
        my_package    = Package()
        my_service    = Service()

        # Pre-parse arguments to check if --from-agent param is passed
        my_args.pre_parse()

        # If --from-agent param is passed, then add -agent to the log filename and make it hidden
        if my_args.from_agent:
            logfile = '.' + date + '_' + time + '_linupdate_' + socket.gethostname() + '-agent.log'

        # Create log file with correct permissions
        Path(logsdir + '/' + logfile).touch()
        Path(logsdir + '/' + logfile).chmod(0o640)

        # Log everything to the log file
        with Log(logsdir + '/' + logfile):
            # Print Logo
            my_app.print_logo()

            # Exit if the user is not root
            if not my_system.is_root():
                print(Fore.YELLOW + 'Must be executed with sudo' + Style.RESET_ALL)
                my_exit.clean_exit(1)

            # Check if the system is supported
            my_system.check()

            # Create lock file
            my_app.set_lock()

            # Create base directories
            my_app.initialize()

            # Generate config file if not exist
            my_app_config.generate_conf()

            # Check if there are missing parameters
            my_app_config.check_conf()

            # Parse arguments
            my_args.parse()

            # Print system & app summary
            my_app.print_summary(my_args.from_agent)

            # Load modules
            my_module.load()

            # Execute pre-update modules functions
            my_module.pre()

            # Execute packages update
            my_package.update(my_args.assume_yes,
                              my_args.ignore_exclude,
                              my_args.check_updates,
                              my_args.dist_upgrade,
                              my_args.keep_oldconf)

            # Execute post-update modules functions
            my_module.post(my_package.summary)

            # Restart services
            my_service.restart(my_package.summary)

            # Check if reboot is required
            if my_system.reboot_required() is True:
                print(' ' + Fore.YELLOW + 'Reboot is required' + Style.RESET_ALL)

    # If an ArgsException is raised, print the error message and do not send an email
    except ArgsException as e:
        print('\n' + Fore.RED + ' ✕ ' + Style.RESET_ALL + str(e) + '\n')
        send_mail = False
        exit_code = 1

    # If an exception is raised, print the error message and send an email
    except Exception as e:
        print('\n' + Fore.RED + ' ✕ ' + Style.RESET_ALL + str(e) + '\n')
        exit_code = 1

    # Exit with exit code and logfile for email report
    my_exit.clean_exit(exit_code, send_mail, logsdir + '/' + logfile)

# Run main function
main()