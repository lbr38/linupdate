# coding: utf-8

# Import libraries
import subprocess
import signal
import sys
import importlib
import subprocess
import time
import configparser
from colorama import Fore, Style
from pathlib import Path

# Import classes
from src.controllers.Module.Module import Module

class Service:
    def __init__(self):
        # Register signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

        self.child_processes = []
        self.child_processes_started = []
        self.moduleController = Module()

        # Systemd unit file path
        self.systemd_unit_file = '/lib/systemd/system/linupdate.service'


    #-----------------------------------------------------------------------------------------------
    #
    #   Service main function
    #
    #-----------------------------------------------------------------------------------------------
    def main(self):
        restart_file = '/tmp/linupdate.restart-needed'

        try:
            print("[linupdate] Hi, I'm linupdate service. I will start all enabled module agents and let them run in background. Stop me and I will stop all module agents.")

            # Wait 3 seconds to let the above message to be read
            time.sleep(3)

            while True:
                # Restart check
                # If a '/tmp/linupdate.restart-needed' file is present, restart linupdate service now
                if Path(restart_file).is_file():
                    print('[reposerver-agent] Linupdate service restart is needed.')

                    try:
                        # List of possible lock files (more could be added in the future)
                        lock_files = ['/tmp/linupdate.reposerver.request.lock']

                        # Wait a bit if there is a lock file to prevent data loss
                        while True:
                            lock_present = 0

                            # Check if lock files are present, if so, wait
                            for lock_file in lock_files:
                                if Path(lock_file).is_file():
                                    print('[reposerver-agent] Lock file ' + lock_file + ' is present, waiting...')
                                    lock_present +=1

                            # Break the loop if no lock file is present
                            if (lock_present == 0):
                                break

                            time.sleep(2)

                        # First delete the restart file
                        Path(restart_file).unlink()

                        print('[reposerver-agent] Restarting linupdate service...')

                        # Then restart linupdate service
                        result = subprocess.run(
                            ['/usr/bin/systemctl restart linupdate'],
                            stdout = subprocess.PIPE, # subprocess.PIPE & subprocess.PIPE are alias of 'capture_output = True'
                            stderr = subprocess.PIPE,
                            universal_newlines = True, # Alias of 'text = True'
                            shell = True
                        )

                        # From here, the service should be restarted and the following lines should not be executed. But if there is an error, then raise an exception:
                        if result.returncode != 0:
                            raise Exception(result.stderr)

                    # If there was an error, then the service has to stop because it could not be restarted
                    # Raise an exception to be caught in the main function, it will stop the service
                    except Exception as e:
                        raise Exception('could not restart linupdate service: ' + str(e))


                # Check for terminated child processes (module agents) and remove them from the list
                for child in self.child_processes[:]:
                    retcode = child['process'].poll()

                    if retcode is not None:
                        # If the process has terminated with an error (exit 1), print a message
                        if retcode != 0:
                            print('[' + child['agent'] + '-agent] Terminated with return code ' + str(retcode) + ' :(')
                            print("[" + child['agent'] + "-agent] I'm dead for now but I will be resurrected soon, please wait or restart linupdate service")

                        # Remove child process from list
                        self.child_processes.remove(child)

                # Retrieve enabled modules
                enabled_modules = self.moduleController.getEnabled()

                # For each enabled module, check if its agent is enabled
                for module in enabled_modules:
                    # Convert module name to uppercase first letter
                    module_capitalize = module.capitalize()

                    # Import python module config class
                    module_import_path = importlib.import_module('src.controllers.Module.' + module_capitalize + '.Config')
                    module_class = getattr(module_import_path, 'Config')

                    # Instantiate module and get module configuration
                    my_module = module_class()
                    module_configuration = my_module.get_conf()

                    # Check if module agent is enabled. If not, skip to next module
                    if not module_configuration['agent']['enabled']:
                        continue

                    # Check if module agent process is already running, if so, skip to next module
                    if any(agent['agent'] == module for agent in self.child_processes):
                        continue

                    # Only start module agent if it has not been started in the last 2 minutes
                    # This is to avoid restarting a failed module agent in a loop and consuming resources, as the service will restart it every 2 minutes
                    # An agent could fail to start or fail when executing a task, so we need to avoid restarting it in a loop
                    if any(agent['agent'] == module for agent in self.child_processes_started):
                        # Calculate the remaining time before the agent can be restarted
                        remaining_time = 120 - (time.time() - [agent['start_time'] for agent in self.child_processes_started if agent['agent'] == module][0])

                        if remaining_time < 120 and remaining_time >= 0:
                            # Print a message with the remaining time before the agent can be restarted (in seconds)
                            print('[linupdate] Delay in restarting the ' + module + ' agent: next start time is in ' + str(int(remaining_time)) + ' seconds')
                            continue

                    # Start module agent
                    print('[linupdate] Starting ' + Fore.GREEN + module + Style.RESET_ALL + ' module agent')

                    # Start module agent as a child process
                    process = subprocess.Popen(
                        ['/opt/linupdate/service.py', module],
                        stdout=sys.stdout,
                        stderr=sys.stderr
                    )

                    # Add child process to list
                    self.child_processes.append({
                        'agent': module,
                        'process': process
                    })

                    # Add child process start timestamp to list, first remove it if it already exists (from a previous start)
                    if any(agent['agent'] == module for agent in self.child_processes_started):
                        self.child_processes_started = [agent for agent in self.child_processes_started if agent['agent'] != module]

                    # Add the new start timestamp
                    self.child_processes_started.append({
                        'agent': module,
                        'start_time': time.time()
                    })

                time.sleep(5)

        except Exception as e:
            print('[linupdate] General error: ' + str(e))
            sys.exit(1)


    #-----------------------------------------------------------------------------------------------
    #
    #   Run a module agent as a child process
    #
    #-----------------------------------------------------------------------------------------------
    def run_agent(self, module_name):
        try:
            # Convert module name to uppercase first letter
            module_name_capitalize = module_name.capitalize()

            print("[" + module_name + "-agent] Hi, I'm " + Fore.GREEN + module_name + Style.RESET_ALL + ' module agent')

            # Import python module agent class
            module_import_path = importlib.import_module('src.controllers.Module.' + module_name_capitalize + '.Agent')
            my_module_agent_class = getattr(module_import_path, 'Agent')()

            # Run module agent main function
            my_module_agent_class.main()

        except Exception as e:
            print('[' + module_name + '-agent] Error: ' + str(e))
            exit(1)


    #-----------------------------------------------------------------------------------------------
    #
    #   Stop all child processes
    #
    #-----------------------------------------------------------------------------------------------
    def stop_child_processes(self):
        if not self.child_processes:
            return

        # Stop all child processes
        for child in self.child_processes:
            # Retrieve agent name and process
            agent = child['agent']
            process = child['process']

            print('Stopping ' + agent + ' module agent')

            # Terminate process
            process.terminate()

            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

            print('Stopped ' + child['agent'] + ' module agent')


    #-----------------------------------------------------------------------------------------------
    #
    #   Signal handler
    #   This function is called when the service receives a SIGTERM or SIGINT signal
    #
    #-----------------------------------------------------------------------------------------------
    def signal_handler(self, sig, frame):
        print('Linupdate service received signal ' + str(sig) + '. Stopping all child processes...')

        try:
            self.stop_child_processes()
            sys.exit(0)
        except Exception as e:
            print('Error while stopping child processes: ' + str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   Get current systemd service CPU priority
    #
    #-----------------------------------------------------------------------------------------------
    def get_cpu_priority(self):
        try:
            config = configparser.ConfigParser()
            config.optionxform = str
            config.read(self.systemd_unit_file)

            # Quit if CPUQuota is not found
            if 'CPUQuota' not in config['Service']:
                raise Exception('CPUQuota not found in systemd unit file')

            # Quit if CPUWeight is not found
            if 'CPUWeight' not in config['Service']:
                raise Exception('CPUWeight not found in systemd unit file')
            
            if config['Service']['CPUWeight'] == '50':
                return 'low'
            if config['Service']['CPUWeight'] == '75':
                return 'medium'
            if config['Service']['CPUWeight'] == '100':
                return 'high'
        except Exception as e:
            raise Exception('Could not get CPU priority: ' + str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   Set systemd service CPU priority
    #
    #-----------------------------------------------------------------------------------------------
    def set_cpu_priority(self, priority: str):
        if priority not in ['low', 'medium', 'high']:
            raise Exception('Priority must be low, medium or high')

        try:
            config = configparser.ConfigParser(interpolation=None)
            config.optionxform = str
            config.read(self.systemd_unit_file)

            # Quit if CPUQuota is not found
            if 'CPUQuota' not in config['Service']:
                raise Exception('CPUQuota not found in systemd unit file')

            # Quit if CPUWeight is not found
            if 'CPUWeight' not in config['Service']:
                raise Exception('CPUWeight not found in systemd unit file')
            
            # Set CPU priority
            if priority == 'low':
                # Set CPUQuota to 50%
                config['Service']['CPUQuota'] = '50%'
                # Set CPUWeight to 50
                config['Service']['CPUWeight'] = '50'
            if priority == 'medium':
                # Set CPUQuota to 75%
                config['Service']['CPUQuota'] = '75%'
                # Set CPUWeight to 75
                config['Service']['CPUWeight'] = '75'
            if priority == 'high':
                # Set CPUQuota to 100%
                config['Service']['CPUQuota'] = '100%'
                # Set CPUWeight to 100
                config['Service']['CPUWeight'] = '100'

            # Write to file
            with open(self.systemd_unit_file, 'w') as f:
                config.write(f)

            # Reload systemd unit
            self.reloadSystemUnit()
        except Exception as e:
            raise Exception('Could not set CPU priority: ' + str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   Get current systemd service memory limit
    #
    #-----------------------------------------------------------------------------------------------
    def get_memory_limit(self):
        try:
            config = configparser.ConfigParser()
            config.optionxform = str
            config.read(self.systemd_unit_file)

            # Quit if MemoryMax is not found
            if 'MemoryMax' not in config['Service']:
                raise Exception('MemoryMax not found in systemd unit file')

            # Get MemoryMax
            return config['Service']['MemoryMax']
        except Exception as e:
            raise Exception('Could not get memory limit: ' + str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   Set systemd service memory limit
    #
    #-----------------------------------------------------------------------------------------------
    def set_memory_limit(self, limit: str):
        if not limit:
            raise Exception('Memory limit must be specified')

        try:
            config = configparser.ConfigParser()
            config.optionxform = str
            config.read(self.systemd_unit_file)

            # Quit if MemoryMax is not found
            if 'MemoryMax' not in config['Service']:
                raise Exception('MemoryMax not found in systemd unit file')

            # Set MemoryMax
            config['Service']['MemoryMax'] = limit

            # Write to file
            with open(self.systemd_unit_file, 'w') as f:
                config.write(f)

            # Reload systemd unit
            self.reloadSystemUnit()
        except Exception as e:
            raise Exception('Could not set memory limit: ' + str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   Get current systemd service OOM score
    #
    #-----------------------------------------------------------------------------------------------
    def get_oom_score(self):
        try:
            config = configparser.ConfigParser()
            config.optionxform = str
            config.read(self.systemd_unit_file)

            # Quit if OOMScoreAdjust is not found
            if 'OOMScoreAdjust' not in config['Service']:
                raise Exception('OOMScoreAdjust not found in systemd unit file')

            # Get OOMScoreAdjust
            return config['Service']['OOMScoreAdjust']
        except Exception as e:
            raise Exception('Could not get OOM score: ' + str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   Set systemd service OOM score
    #
    #-----------------------------------------------------------------------------------------------
    def set_oom_score(self, score: int):
        if int(score) < -1000 or int(score) > 1000:
            raise Exception('OOM score must be between -1000 and 1000')

        try:
            config = configparser.ConfigParser()
            config.optionxform = str
            config.read(self.systemd_unit_file)

            # Quit if OOMScoreAdjust is not found
            if 'OOMScoreAdjust' not in config['Service']:
                raise Exception('OOMScoreAdjust not found in systemd unit file')
            
            # Set OOMScoreAdjust
            config['Service']['OOMScoreAdjust'] = str(score)

            # Write to file
            with open(self.systemd_unit_file, 'w') as f:
                config.write(f)

            # Reload systemd unit
            self.reloadSystemUnit()
        except Exception as e:
            raise Exception('Could not set OOM score: ' + str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   Reload linupdate systemd unit
    #
    #-----------------------------------------------------------------------------------------------
    def reloadSystemUnit(self):
        result = subprocess.run(
            ['/usr/bin/systemctl', 'daemon-reload'],
            stdout = subprocess.PIPE, # subprocess.PIPE & subprocess.PIPE are alias of 'capture_output = True'
            stderr = subprocess.PIPE,
            universal_newlines = True,  # Alias of 'text = True'
        )

        # Quit if an error occurred
        if result.returncode != 0:
            raise Exception('Error while reloading systemd unit: ' + result.stderr)
