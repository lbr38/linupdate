# coding: utf-8

# Import libraries
from colorama import Fore, Style
import time
import pyinotify
import threading
import websocket
import json
import sys
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

    #-----------------------------------------------------------------------------------------------
    #
    #   Enable or disable agent
    #
    #-----------------------------------------------------------------------------------------------
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


    #-----------------------------------------------------------------------------------------------
    #
    #   Enable or disable agent listening
    #
    #-----------------------------------------------------------------------------------------------
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


    #-----------------------------------------------------------------------------------------------
    #
    #   General checks for running the agent
    #
    #-----------------------------------------------------------------------------------------------
    def run_general_checks(self):
        enabled_modules = self.moduleController.getEnabled()

        # Checking that reposerver module is enabled, if not quit (but with error 0 because it could have been disabled on purpose)
        if 'reposerver' not in enabled_modules:
            print('[reposerver-agent] Reposerver module is disabled, quitting.')
            sys.exit(0)

        # Retrieving configuration
        self.configuration = self.configController.get_conf()

        # Checking that reposerver URL is set, if not quit
        if not self.configuration['reposerver']['url']:
            print('[reposerver-agent] Reposerver URL is not set. Quitting.')
            sys.exit(1)

        # Check that this host has an auth id and token
        if not self.configuration['client']['auth']['id'] or not self.configuration['client']['auth']['token']:
            print('[reposerver-agent] No authentication id and token set, is this host registered on the Repomanager server? Quitting.')
            sys.exit(1)

        # Checking that reposerver agent is enabled, if not quit (but with error 0 because it could have been disabled on purpose)
        if not self.configuration['agent']['enabled']:
            print('[reposerver-agent] Reposerver agent is disabled. Quitting.')
            sys.exit(0)
        
        # Checking that a log file exists for yum/dnf or apt
        if Path('/var/log/yum.log').is_file():
            self.log_file = '/var/log/yum.log'
        elif Path('/var/log/dnf.log').is_file():
            self.log_file = '/var/log/dnf.log'
        elif Path('/var/log/apt/history.log').is_file():
            self.log_file = '/var/log/apt/history.log'
        else:
            raise Exception('no log file found for yum/dnf or apt')


    #-----------------------------------------------------------------------------------------------
    #
    #   Run functions when an inotify event is detected
    #
    #-----------------------------------------------------------------------------------------------
    def on_inotify_change(self, ev):
        print('[reposerver-agent] New event has been detected in ' + self.log_file + ' - sending history to the Repomanager server.')
        self.reposerverStatusController.sendFullHistory(4)


    #-----------------------------------------------------------------------------------------------
    #
    #   Run inotify process to scan for package events
    #
    #-----------------------------------------------------------------------------------------------
    def run_inotify_package_event(self):
        print('[reposerver-agent] Starting package event monitoring from ' + self.log_file)

        try:
            # Set inotify process as running to prevent multiple processes from running
            self.inotify_is_running = True

            watch_manager = pyinotify.WatchManager()
            # TODO : to test
            # quiet=False => raise Exception
            # watch_manager.add_watch(self.log_file, pyinotify.IN_MODIFY, self.on_inotify_change)
            watch_manager.add_watch(self.log_file, pyinotify.IN_CLOSE_WRITE, self.on_inotify_change, quiet=False)
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


    #-----------------------------------------------------------------------------------------------
    #
    #   On message received from the websocket
    #
    #-----------------------------------------------------------------------------------------------
    def websocket_on_message(self, ws, message):
        # Decode JSON message
        message = json.loads(message)

        # If the message contains 'request'
        if 'request' in message:
            # Case the request is 'authenticate', then authenticate to the reposerver
            if message['request'] == 'authenticate':
                print('[reposerver-agent] Authenticating to the reposerver')

                id = self.configuration['client']['auth']['id']
                token = self.configuration['client']['auth']['token']

                # Send id and token to authenticate
                self.websocket.send(json.dumps({'action': 'authenticate', 'id': id, 'token': token}))

            elif message['request'] == 'send-general-status':
                print('[reposerver-agent] Reposerver requested general status')
                self.reposerverStatusController.sendGeneralStatus()
            else:
                print('[reposerver-agent] Unknown request from reposerver: ' + message['request'])

        # If the message contains 'info'
        if 'info' in message:
            print('[reposerver-agent] Received message from reposerver: ' + message['info'])


    #-----------------------------------------------------------------------------------------------
    #
    #   On error from the websocket
    #
    #-----------------------------------------------------------------------------------------------
    def websocket_on_error(self, ws, error):
        raise Exception('Error : ' + str(error))


    #-----------------------------------------------------------------------------------------------
    #
    #   On websocket connection closed
    #
    #-----------------------------------------------------------------------------------------------
    def websocket_on_close(self, ws, close_status_code, close_msg):
        print('[reposerver-agent] Reposerver websocket connection closed with status code: ' + str(close_status_code) + ' and message: ' + close_msg)
        raise Exception('reposerver websocket connection closed')


    #-----------------------------------------------------------------------------------------------
    #
    #   On websocket connection opened
    #
    #-----------------------------------------------------------------------------------------------
    def websocket_on_open(self, ws):
        print('[reposerver-agent] Opening connection with reposerver')


    #-----------------------------------------------------------------------------------------------
    #
    #   Start websocket client
    #
    #-----------------------------------------------------------------------------------------------
    def websocket_client(self):
        try:
            # Replace http by ws, or https by wss
            reposerver_ws_url = self.configuration['reposerver']['url'].replace('http', 'ws').replace('https', 'wss')

            # Set websocket process as running to prevent multiple processes from running
            self.websocket_is_running = True

            # Set to True for debugging
            websocket.enableTrace(False)

            # Open websocket connection
            self.websocket = websocket.WebSocketApp(reposerver_ws_url + '/ws',
                                        on_open=self.websocket_on_open,
                                        on_message=self.websocket_on_message,
                                        on_error=self.websocket_on_error,
                                        on_close=self.websocket_on_close)

            # Run websocket
            self.websocket.on_open = self.websocket_on_open
            self.websocket.run_forever()

        except KeyboardInterrupt:
            self.websocket_is_running = False
            self.websocket_exception = str(e)
        except Exception as e:
            self.websocket_is_running = False
            self.websocket_exception = str(e)
        

    #-----------------------------------------------------------------------------------------------
    #
    #   Reposerver agent main function
    #
    #-----------------------------------------------------------------------------------------------
    def main(self):
        counter = 0
        self.child_processes = []
        self.child_processes_started = []
        self.inotify_is_running = False
        self.inotify_exception = None
        self.websocket_is_running = False
        self.websocket_exception = None

        # Checking that all the necessary elements are present for the agent execution
        self.run_general_checks()

        # Executing regular tasks
        while True:
            # Checking that all the necessary elements are present for the agent execution.
            # This is checked every time in case that a configuration change has been made in the configuration file
            self.run_general_checks()

            # Regulary sending data to the Repomanager server (every hour)
            # 3600 / 5sec (sleep 5) = 720
            # if counter == 0 or counter == 720:
            #     # Sending full status
            #     print('[reposerver-agent] Periodically sending informations about this host to the repomanager server')
            #     self.reposerverStatusController.sendGeneralStatus()
            #     self.reposerverStatusController.sendPackagesStatus()

            #     # Reset counter
            #     counter = 0

            # If no inotify process is running, then execute it in background
            # if not self.inotify_is_running:
            #     try:
            #         # If there was an exception in the last inotify process, then raise it
            #         if self.inotify_exception:
            #             raise Exception(self.inotify_exception)

            #         thread = threading.Thread(target=self.run_inotify_package_event)
            #         thread.daemon = True
            #         thread.start()
            #     except Exception as e:
            #         raise Exception('package event monitoring failed: ' + str(e))

            # If agent listening is enabled, open websocket
            if self.configuration['agent']['listen']['enabled']:
                if not self.websocket_is_running:
                    try:
                        # If there was an exception in the last websocket process, then raise it
                        if self.websocket_exception:
                            raise Exception(self.websocket_exception)

                        thread = threading.Thread(target=self.websocket_client)
                        thread.daemon = True
                        thread.start()
                    except Exception as e:
                        raise Exception('reposerver websocket connection failed: ' + str(e))

            time.sleep(5)

            counter+=1
