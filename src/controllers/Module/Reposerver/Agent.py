# coding: utf-8

# Import libraries
from colorama import Fore, Style
import subprocess
import time
import pyinotify
import threading
from pathlib import Path

# Import classes
from src.controllers.Module.Module import Module
from src.controllers.Module.Reposerver.Status import Status
from src.controllers.Module.Reposerver.Config import Config

class Agent:
    def __init__(self):
        self.moduleController = Module()
        self.configController = Config()
        self.reposerverStatusController = Status()

    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Enable or disable agent
    #
    #-------------------------------------------------------------------------------------------------------------------
    def setEnable(self, value: bool):
        try:
            # Get current configuration
            configuration = self.configController.get_conf()

            # Set allow_repos_update
            configuration['agent']['enabled'] = value

            # Write config file
            self.configController.write_conf(configuration)

            if value:
                print(' Reposerver agent ' + Fore.GREEN + 'enabled' + Style.RESET_ALL)
            else:
                print(' Reposerver agent ' + Fore.YELLOW + 'disabled' + Style.RESET_ALL)

        except Exception as e:
            raise Exception('could not set agent enable to ' + str(value) + ': ' + str(e))


    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Get current agent listening interface
    #
    #-------------------------------------------------------------------------------------------------------------------
    def getListenInterface(self):
        # Get current configuration
        configuration = self.configController.get_conf()

        # Return watch_interface
        return configuration['agent']['listen']['interface']


    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Set agent listening interface
    #
    #-------------------------------------------------------------------------------------------------------------------
    def setListenInterface(self, value: str):
        try:
            # Get current configuration
            configuration = self.configController.get_conf()

            # Set listen interface
            configuration['agent']['listen']['interface'] = value

            # Write config file
            self.configController.write_conf(configuration)
        
            print(' Agent listening interface set to ' + Fore.GREEN + value + Style.RESET_ALL)
        
        except Exception as e:
            raise Exception('could not set agent listening interface to ' + value + ': ' + str(e))


    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Enable or disable agent listening
    #
    #-------------------------------------------------------------------------------------------------------------------
    def setListenEnable(self, value: bool):
        try:
            # Get current configuration
            configuration = self.configController.get_conf()

            # Set allow_repos_update
            configuration['agent']['listen']['enabled'] = value

            # Write config file
            self.configController.write_conf(configuration)

            if value:
                print(' Agent listening ' + Fore.GREEN + 'enabled' + Style.RESET_ALL)
            else:
                print(' Agent listening ' + Fore.YELLOW + 'disabled' + Style.RESET_ALL)

        except Exception as e:
            raise Exception('could not set agent listening enable to ' + str(value) + ': ' + str(e))


    #-------------------------------------------------------------------------------------------------------------------
    #
    #   General checks for running the agent
    #
    #-------------------------------------------------------------------------------------------------------------------
    def run_general_checks(self):
        enabled_modules = self.moduleController.getEnabled()

        # Checking that reposerver module is enabled, if not quit (but with error 0 because it could have been disabled on purpose)
        if 'reposerver' not in enabled_modules:
            print('[reposerver-agent] Reposerver module is disabled, quitting.')
            exit(0)
        
        # Checking that a configuration file exists for reposerver module
        if not Path('/etc/linupdate/modules/reposerver.yml').is_file():
            raise Exception('reposerver module configuration file /etc/linupdate/modules/reposerver.yml does not exist')
        
        # Checking that reposerver agent is enabled, if not quit (but with error 0 because it could have been disabled on purpose)
        configuration = self.configController.get_conf()
        if not configuration['agent']['enabled']:
            print('[reposerver-agent] Reposerver agent is disabled, quitting.')
            exit(0)
        
        # Checking that a log file exists for yum/dnf or apt
        if Path('/var/log/yum.log').is_file():
            self.log_file = '/var/log/yum.log'
        elif Path('/var/log/dnf.log').is_file():
            self.log_file = '/var/log/dnf.log'
        elif Path('/var/log/apt/history.log').is_file():
            self.log_file = '/var/log/apt/history.log'
        else:
            raise Exception('no log file found for yum/dnf or apt')


    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Run functions when an inotify event is detected
    #
    #-------------------------------------------------------------------------------------------------------------------
    def on_inotify_change(self, ev):
        print('[reposerver-agent] New event has been detected in ' + self.log_file + ' - sending history to the Repomanager server.')
        self.reposerverStatusController.sendFullHistory(4)


    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Run inotify process to scan for package events
    #
    #-------------------------------------------------------------------------------------------------------------------
    def run_inotify_package_event(self):
        print('[reposerver-agent] Starting package event monitoring from ' + self.log_file)

        try:
            # Set inotify process as running to prevent multiple processes from running
            self.inotify_is_running = True

            watch_manager = pyinotify.WatchManager()
            # watch_manager.add_watch(self.log_file, pyinotify.IN_MODIFY, self.on_inotify_change)
            # quiet=False => raise Exception
            # watch_manager.add_watch(self.log_file, pyinotify.IN_CLOSE_WRITE, self.on_inotify_change, quiet=False)
            # TODO debug
            watch_manager.add_watch('/tmp/toto', pyinotify.IN_CLOSE_WRITE, self.on_inotify_change, quiet=False)
            notifier = pyinotify.Notifier(watch_manager)
            notifier.loop()

        # If an exception is raised, then set inotify process as not running and store the exception to
        # be read by the main function (cannot raise an exception to be read by the main function, it does not work, so store it instead)
        except pyinotify.WatchManagerError as e:
            self.inotify_is_running = False
            self.inotify_exception = str(e)
        except Exception as e:
            self.inotify_is_running = False
            self.inotify_exception = str(e)


    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Reposerver agent main function
    #
    #-------------------------------------------------------------------------------------------------------------------
    def main(self):
        counter = 0
        self.ngrep_cmd = 'ngrep -q -t -W byline'
        self.ngrep_interface = None
        self.child_processes = []
        self.child_processes_started = []
        self.inotify_is_running = False
        self.inotify_exception = None

        # Checking that all the necessary elements are present for the agent execution
        self.run_general_checks()

        # Get current configuration
        configuration = self.configController.get_conf()

        # Retrieving network interface to scan if specified
        interface = configuration['agent']['listen']['interface']

        # If network interface is specified with "auto" or is empty, then try to automatically retrieve default interface
        if interface == 'auto' or not interface:
            # Get default network interface
            result = subprocess.run(
                ["/usr/sbin/route | /usr/bin/grep '^default' | /usr/bin/grep -o '[^ ]*$'"],
                stdout = subprocess.PIPE, # subprocess.PIPE & subprocess.PIPE are alias of 'capture_output = True'
                stderr = subprocess.PIPE,
                universal_newlines = True, # Alias of 'text = True'
                shell = True
            )

            if result.returncode != 0:
                raise Exception('could not determine default network interface on which to listen: ' + result.stderr)

            interface = result.stdout.strip()

            # Count the number of lines returned
            lines = interface.split('\n')

            # If more than one line is returned, then there is a problem
            if len(lines) > 1:
                raise Exception('could not determine default network interface on which to listen: multiple default interfaces have been detected')
            
        # Taking into account the network interface
        self.ngrep_interface = interface

        # Executing regular tasks
        while True:
            # Checking that all the necessary elements are present for the agent execution.
            # This is checked every time in case that a configuration change has been made in the configuration file
            self.run_general_checks()

            # Regulary sending data to the Repomanager server (every hour)
            # 3600 / 5sec (sleep 5) = 720
            if counter == 0 or counter == 720:
                # Sending full status
                print('[reposerver-agent] Periodically sending informations about this host to the repomanager server')
                self.reposerverStatusController.sendGeneralStatus()
                self.reposerverStatusController.sendPackagesStatus()

                # Reset counter
                counter = 0

            # If no inotify process is running, then execute it in background
            if not self.inotify_is_running:
                try:
                    # If there was an exception in the last inotify process, then raise it
                    if self.inotify_exception:
                        raise Exception(self.inotify_exception)

                    thread = threading.Thread(target=self.run_inotify_package_event)
                    thread.daemon = True
                    thread.start()
                except Exception as e:
                    raise Exception('package event monitoring failed: ' + str(e))

            # If ngrep scans are enabled, then execute them in background
            # if configuration['agent']['listen']['enabled']:
                # Monitor general informations sending requests
                # TODO
                # ngrep_general_update_request

                # Monitor packages informations sending requests
                # TODO
                # ngrep_packages_status_request

                # Monitor package update requests
                # TODO
                # ngrep_packages_update_requested

            time.sleep(5)

            counter+=1
