# coding: utf-8

# Import libraries
import time
import pyinotify
import threading
import websocket
import json
import sys
from pathlib import Path
from shutil import rmtree
import os

# Import classes
from src.controllers.Log import Log
from src.controllers.Module.Module import Module
from src.controllers.Module.Reposerver.Status import Status
from src.controllers.Module.Reposerver.Config import Config
from src.controllers.Package.Package import Package
from src.controllers.App.Utils import Utils

class Agent:
    def __init__(self):
        self.moduleController = Module()
        self.configController = Config()
        self.reposerverStatusController = Status()
        self.packageController = Package()

        # Set default values
        self.authenticated = False

        # Root directory for the requests logs
        self.request_dir = '/opt/linupdate/tmp/reposerver/requests'

        # Create the directories to store the logs if they do not exist
        if not Path(self.request_dir).is_dir():
            Path(self.request_dir).mkdir(parents=True, exist_ok=True)


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
            print('[reposerver-agent] No authentication id and token set, is this host registered to a Repomanager server? Quitting.')
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
        # If latest event was less than 120 seconds ago, then do not send again the history
        if self.last_inotify_event_time and time.time() - self.last_inotify_event_time < 120:
            return

        # Define new last event time
        self.last_inotify_event_time = time.time()

        # /var/log/dnf.log issue: wait before sending the history because it might have 
        # been triggered by another history sending (from a request from the Repomanager server for example) as 
        # even the 'dnf history' command is logged in the dnf.log file
        # So just wait a bit to don't send both history at the same time...
        if self.log_file == '/var/log/dnf.log':
            time.sleep(15)

        # Send the history
        print('[reposerver-agent] New event has been detected in ' + self.log_file + ' - sending history to the Repomanager server.')
        self.reposerverStatusController.send_packages_history()


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
            self.last_inotify_event_time = None

            watch_manager = pyinotify.WatchManager()
            # TODO: to test when there are multiple events at once in the log file
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
    #   Set request status
    #
    #-----------------------------------------------------------------------------------------------
    def set_request_status(self, request_id, status):
        json_data = {
            'response-to-request': {
                'request-id': request_id,
                'status': status
            }
        }

        # Send the response
        self.websocket.send(json.dumps(json_data))


    #-----------------------------------------------------------------------------------------------
    #
    #   Send remaining requests logs to the reposerver
    #
    #-----------------------------------------------------------------------------------------------
    def send_remaining_requests_logs(self):
        try:
            # Quit if not authenticated to the reposerver
            if not self.authenticated:
                return

            # Get all requests logs directories
            requests_dirs = Path(self.request_dir).iterdir()

            # Then order them by name
            requests_dirs = sorted(requests_dirs, key=lambda x: x.name)

            # For each directory, get its name (request id)
            for request_dir in requests_dirs:
                try:
                    status = 'unknown'
                    summary = None
                    error = None
                    logcontent = None

                    # Check if it is a directory
                    if not request_dir.is_dir():
                        continue

                    # Only process directories with a creation time older than 5 minutes
                    if time.time() - os.path.getmtime(request_dir) < 300:
                        continue

                    # If the directory is empty, then delete it
                    if not any(request_dir.iterdir()):
                        rmtree(request_dir)
                        continue

                    # Initialize json
                    json_response = {
                        'response-to-request': {}
                    }

                    # Get request id and set it in the json
                    request_id = request_dir.name
                    json_response['response-to-request']['request-id'] = request_id

                    # Get general log, if log file exists, and set it in the json
                    if Path(self.request_dir + '/' + request_id + '/log').is_file():
                        with open(self.request_dir + '/' + request_id + '/log', 'r') as file:
                            # Get log content and remove ANSI escape codes
                            logcontent = Utils().clean_log(file.read())

                    # Get status, if log file exists, and set it in the json
                    if Path(self.request_dir + '/' + request_id + '/status').is_file():
                        with open(self.request_dir + '/' + request_id + '/status', 'r') as file:
                            status = file.read().strip()

                    # Get summary, if log file exists, and set it in the json
                    if Path(self.request_dir + '/' + request_id + '/summary').is_file():
                        with open(self.request_dir + '/' + request_id + '/summary', 'r') as file:
                            summary = file.read().strip()
                            # Convert the string to a json
                            summary = json.loads(summary)

                    # Get error, if log file exists, and set it in the json
                    if Path(self.request_dir + '/' + request_id + '/error').is_file():
                        with open(self.request_dir + '/' + request_id + '/error', 'r') as file:
                            error = file.read().strip()

                    if status:
                        json_response['response-to-request']['status'] = status

                    if summary:
                        json_response['response-to-request']['summary'] = summary

                    if error:
                        json_response['response-to-request']['error'] = error

                    if logcontent:
                        json_response['response-to-request']['log'] = logcontent

                    # Send the response
                    print('[reposerver-agent] Sending remaining requests logs for request id #' + request_id + ' with status: ' + status)
                    self.websocket.send(json.dumps(json_response))

                    # Delete the directory and all its content
                    if Path(self.request_dir + '/' + request_id).is_dir():
                        rmtree(self.request_dir + '/' + request_id)
                except Exception as e:
                    raise Exception('could not send remaining requests logs for request id #' + request_id + ': ' + str(e))
        except Exception as e:
            print('[reposerver-agent] Error: ' + str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   On message received from the websocket
    #
    #-----------------------------------------------------------------------------------------------
    def websocket_on_message(self, ws, message):
        # Default values
        request_id = None
        summary = None
        status = None
        error = None

        # Update parameters default values
        dry_run = False
        ignore_exclusions = False
        keep_oldconf = True
        full_upgrade = False

        # Decode JSON message
        message = json.loads(message)

        # Default log file path, could be overwritten if request id is present
        log = '/opt/linupdate/tmp/reposerver/requests/log'

        # Lock to prevent service restart while processing the request
        lock = '/tmp/linupdate.reposerver.request.lock'

        # Default json response
        json_response = {
            'response-to-request': {
                'request-id': '',
                'status': '',
                'summary': '',
                'log': ''
            }
        }

        try:
            # Create a lock file to prevent service restart while processing the request
            if not Path(lock).is_file():
                Path(lock).touch()

            # If the message contains 'request'
            if 'request' in message:
                try:
                    # Retrieve request Id if any (authenticate request does not have an id)
                    if 'request-id' in message:
                        request_id = str(message['request-id'])

                        # Create a new directory for the request id
                        if not Path(self.request_dir + '/' + request_id).is_dir():
                            Path(self.request_dir + '/' + request_id).mkdir(parents=True, exist_ok=True)

                        # Set new log files path for the request id
                        log         = self.request_dir + '/' + request_id + '/log'
                        log_status  = self.request_dir + '/' + request_id + '/status'
                        log_error   = self.request_dir + '/' + request_id + '/error'
                        log_summary = self.request_dir + '/' + request_id + '/summary'

                    # Case the request is 'authenticate', then authenticate to the reposerver
                    if message['request'] == 'authenticate':
                        print('[reposerver-agent] Authenticating to the reposerver')

                        id = self.configuration['client']['auth']['id']
                        token = self.configuration['client']['auth']['token']

                        # Send a response to authenticate to the reposerver, with id and token
                        self.websocket.send(json.dumps({'response-to-request': {'request': 'authenticate', 'auth-id': id, 'token': token}}))

                    # Case the request is 'request-general-infos', then send general informations to the reposerver
                    elif message['request'] == 'request-general-infos':
                        print('[reposerver-agent] Reposerver requested general informations')
                        with Log(log):
                            self.reposerverStatusController.send_general_info()

                    # Case the request is 'request-packages-infos', then send packages informations to the reposerver
                    elif message['request'] == 'request-packages-infos':
                        print('[reposerver-agent] Reposerver requested packages informations')

                        # Send a response to the reposerver to make the request as running
                        self.set_request_status(request_id, 'running')

                        # Log everything to the log file
                        with Log(log):
                            self.reposerverStatusController.send_packages_info()

                    # Case the request is 'request-all-packages-update', then update all packages
                    elif message['request'] == 'request-all-packages-update':
                        print('[reposerver-agent] Reposerver requested all packages update')

                        # Try to retrieve the update params
                        if 'data' in message:
                            if 'update-params' in message['data']:
                                if 'dry-run' in message['data']['update-params']:
                                    dry_run = Utils().stringToBoolean(message['data']['update-params']['dry-run'])
                                if 'ignore-exclusions' in message['data']['update-params']:
                                    ignore_exclusions = Utils().stringToBoolean(message['data']['update-params']['ignore-exclusions'])
                                if 'keep-config-files' in message['data']['update-params']:
                                    keep_oldconf = Utils().stringToBoolean(message['data']['update-params']['keep-config-files'])
                                if 'full-upgrade' in message['data']['update-params']:
                                    full_upgrade = Utils().stringToBoolean(message['data']['update-params']['full-upgrade'])

                        # Send a response to the reposerver to make the request as running
                        self.set_request_status(request_id, 'running')

                        # Log everything to the log file
                        with Log(log):
                            self.packageController.update([], True, ignore_exclusions, False, full_upgrade, keep_oldconf, dry_run)

                            # TODO
                            # Restart/reload services if the user said so
                            # Execute reposever post-update actions

                        # Send a summary to the reposerver, with the summary of the update (number of packages updated or failed)
                        summary = self.packageController.summary

                    # Case the request is 'request-packages-update', then update a list of specific packages
                    # A list of packages must be provided in the message
                    elif message['request'] == 'request-packages-update':
                        print('[reposerver-agent] Reposerver requested to update a list of packages')
                        # Try to retrieve the update packages and params
                        if 'data' in message:
                            if 'update-params' in message['data']:
                                if 'dry-run' in message['data']['update-params']:
                                    dry_run = Utils().stringToBoolean(message['data']['update-params']['dry-run'])
                                if 'ignore-exclusions' in message['data']['update-params']:
                                    ignore_exclusions = Utils().stringToBoolean(message['data']['update-params']['ignore-exclusions'])
                                if 'keep-config-files' in message['data']['update-params']:
                                    keep_oldconf = Utils().stringToBoolean(message['data']['update-params']['keep-config-files'])
                                if 'full-upgrade' in message['data']['update-params']:
                                    full_upgrade = Utils().stringToBoolean(message['data']['update-params']['full-upgrade'])

                            # If a list of packages is provided, then the update can be performed
                            if 'packages' in message['data'] and len(message['data']['packages']) > 0:
                                # Send a response to the reposerver to make the request as running
                                self.set_request_status(request_id, 'running')

                                # Log everything to the log file
                                with Log(log):
                                    self.packageController.update(message['data']['packages'], True, ignore_exclusions, False, full_upgrade, keep_oldconf, dry_run)

                                # Send a summary to the reposerver, with the summary of the installation (number of packages installed or failed)
                                summary = self.packageController.summary
                    else:
                        raise Exception('unknown request sent by reposerver: ' + message['request'])

                    # If request was successful
                    status = 'completed'

                # If request failed
                except Exception as e:
                    print('[reposerver-agent] Error: ' + str(e))
                    status = 'failed'
                    error = str(e)

                finally:
                    # If there was a request id, then send a response to reposerver to make the request as completed
                    if request_id:
                        # First, save the log, status, summary and error to a file, in case the message cannot be sent
                        # It will be sent later when the agent is running again
                        if status:
                            with open(log_status, 'w') as file:
                                file.write(status)
                        if summary:
                            with open(log_summary, 'w') as file:
                                # Convert summary to string to write it to the file
                                json.dump(summary, file)
                        if error:
                            with open(log_error, 'w') as file:
                                file.write(error)

                        # Then try to send the response

                        # Set request id
                        json_response['response-to-request']['request-id'] = request_id

                        # Set status
                        json_response['response-to-request']['status'] = status

                        # If there was an error
                        if error:
                            json_response['response-to-request']['error'] = error

                        # If there is a summary
                        if summary:
                            json_response['response-to-request']['summary'] = summary

                        # If there is a log file
                        if log and Path(log).is_file():
                            # Get log file content
                            try:
                                with open(log, 'r') as file:
                                    # Get log content and remove ANSI escape codes
                                    logcontent = Utils().clean_log(file.read())
                            except Exception as e:
                                # If content could not be read, then generate an error message
                                logcontent = 'Error: could not read log file: ' + str(e)                        

                            json_response['response-to-request']['log'] = logcontent

                        # Try to send the response to the reposerver
                        # Note: impossible to use try/except here, because no exception is raised directly, 
                        # if there is an error then it is the on_error function that is called
                        self.websocket.send(json.dumps(json_response))

            # If the message contains 'info'
            if 'info' in message:
                print('[reposerver-agent] Received info message from reposerver: ' + message['info'])

                # If the message is 'Authentication successful', then set authenticated to True
                if message['info'] == 'Authentication successful':
                    self.authenticated = True

                # If the message is 'Request response received', then delete the remaining logs
                if message['info'] == 'Request response received':
                    # First retrieve the request id
                    if 'request-id' in message:
                        request_id = message['request-id']

                        # If the server has tell what kinf of data it has received, then delete the corresponding files if they exist
                        if 'data' in message:
                            for data in message['data']:
                                if Path(self.request_dir + '/' + request_id + '/' + data).is_file():
                                    Path(self.request_dir + '/' + request_id + '/' + data).unlink()

            # If the message contains 'error'
            if 'error' in message:
                print('[reposerver-agent] Received error message from reposerver: ' + message['error'])

        # If all goes well or if an exception is raised, then delete the lock file
        finally:
            # Delete the lock file
            if Path(lock).is_file():
                Path(lock).unlink()


    #-----------------------------------------------------------------------------------------------
    #
    #   On error from the websocket
    #
    #-----------------------------------------------------------------------------------------------
    def websocket_on_error(self, ws, error):
        raise Exception('Websocket error: ' + str(error))


    #-----------------------------------------------------------------------------------------------
    #
    #   On websocket connection closed
    #
    #-----------------------------------------------------------------------------------------------
    def websocket_on_close(self, ws, close_status_code, close_msg):
        print('[reposerver-agent] Reposerver websocket connection closed with status code: ' + str(close_status_code) + ' and message: ' + close_msg)
        self.authenticated = False
        raise Exception('reposerver websocket connection closed')


    #-----------------------------------------------------------------------------------------------
    #
    #   On websocket connection opened
    #
    #-----------------------------------------------------------------------------------------------
    def websocket_on_open(self, ws):
        print('[reposerver-agent] Opened connection with reposerver')

        # Send connection type to the reposerver
        self.websocket.send(
            json.dumps({
                'connection-type': 'host'
            })
        )


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
            # Using lambda to pass arguments to the functions, this is necessary for older versions of python websocket
            self.websocket = websocket.WebSocketApp(reposerver_ws_url + '/ws',
                            on_open=lambda ws: self.websocket_on_open(ws),
                            on_message=lambda ws, message: self.websocket_on_message(ws, message),
                            on_error=lambda ws, error: self.websocket_on_error(ws, error),
                            on_close=lambda ws, close_status_code, close_msg: self.websocket_on_close(ws, close_status_code, close_msg))
            
            # Clean version but not working with older versions of python websocket:
            # Open websocket connection
            # self.websocket = websocket.WebSocketApp(reposerver_ws_url + '/ws',
            #                             on_open=self.websocket_on_open,
            #                             on_message=self.websocket_on_message,
            #                             on_error=self.websocket_on_error,
            #                             on_close=self.websocket_on_close)

            # Run websocket
            # self.websocket.on_open = self.websocket_on_open
            self.websocket.run_forever()

        except KeyboardInterrupt as e:
            self.websocket_is_running = False
            self.websocket_exception = str(e)
            self.authenticated = False
        except Exception as e:
            self.websocket_is_running = False
            self.websocket_exception = str(e)
            self.authenticated = False
        

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
                self.reposerverStatusController.send_general_info()
                self.reposerverStatusController.send_packages_info()

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
                    
                # If some requests logs were not sent (because the program crashed or the reposerver was unavailable for eg), then send them now
                self.send_remaining_requests_logs()

            time.sleep(5)

            counter+=1
