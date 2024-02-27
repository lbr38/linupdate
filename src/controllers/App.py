# coding: utf-8

# Import constants
from constant import *

# Import libraries
from datetime import datetime
from pathlib import Path
from colorama import Fore, Back, Style
import socket
import yaml
import getpass

# Import classes
from src.controllers.System import System

class App:
    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Return current version of the application
    #
    #-------------------------------------------------------------------------------------------------------------------
    def getVersion(self):
        file = open(ROOT + '/version', 'r')
        version = file.read()

        return version


    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Return linupdate configuration from config file
    #
    #-------------------------------------------------------------------------------------------------------------------
    def getConf(self):
        # Open YAML config file:
        with open(CONF) as stream:
            try:
                # Read YAML and return profile
                data = yaml.safe_load(stream)
                return data

            except yaml.YAMLError as exception:
                print(exception)


    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Create lock file
    #
    #-------------------------------------------------------------------------------------------------------------------
    def setLock(self):
        Path('/tmp/linupdate.lock').touch()

    
    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Remove lock file
    #
    #-------------------------------------------------------------------------------------------------------------------
    def removeLock(self):
        Path('/tmp/linupdate.lock').unlink()


    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Create base directories
    #
    #-------------------------------------------------------------------------------------------------------------------
    def initialize(self):
        Path(ROOT).mkdir(parents=True, exist_ok=True)
        Path(ETC_DIR).mkdir(parents=True, exist_ok=True)
        Path(MODULES_CONF_DIR).mkdir(parents=True, exist_ok=True)
        Path(MODULES_DIR).mkdir(parents=True, exist_ok=True)
        Path(MODULES_ENABLED_DIR).mkdir(parents=True, exist_ok=True)
        Path(AGENTS_ENABLED_DIR).mkdir(parents=True, exist_ok=True)
        Path(SERVICE_DIR).mkdir(parents=True, exist_ok=True)
        Path(LOGS_DIR).mkdir(parents=True, exist_ok=True)

        # Set permissions
        Path(ROOT).chmod(0o750)
        Path(SRC_DIR).chmod(0o750)
        Path(ETC_DIR).chmod(0o750)
        Path(MODULES_CONF_DIR).chmod(0o750)
        Path(MODULES_DIR).chmod(0o750)
        Path(MODULES_ENABLED_DIR).chmod(0o750)
        Path(AGENTS_ENABLED_DIR).chmod(0o750)
        Path(SERVICE_DIR).chmod(0o750)
        Path(LOGS_DIR).chmod(0o750)

        # Check if the .src directory is empty
        if not len(list(Path(SRC_DIR).rglob('*'))):
            print(Fore.YELLOW + 'Linupdate core files are missing. You might reinstall linupdate.' + Style.RESET_ALL)
            exit(1)


    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Check if the config file exists and if it contains the required parameters
    #
    #-------------------------------------------------------------------------------------------------------------------
    def checkConf(self):
        # Check if the config file exists
        if not Path(CONF).is_file():
            print(Fore.YELLOW + 'Configuration file "' + CONF + '" is missing.' + Style.RESET_ALL)
            exit(1)

        # Check if profile is set in the config file
        if not self.getProfile():
            print(Fore.YELLOW + 'Profile is missing in the configuration file.' + Style.RESET_ALL)
            exit(1)

        # Check if environment is set in the config file
        if not self.getEnvironment():
            print(Fore.YELLOW + 'Environment is missing in the configuration file.' + Style.RESET_ALL)
            exit(1)


    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Generate main config file if not exist
    #
    #-------------------------------------------------------------------------------------------------------------------
    def generateConf(self):
        # Quit if the config file already exists
        if Path(CONF).is_file():
            return

        # Minimal config file
        data = {
            'main': {
                'profile': 'PC',
                'environment': 'prod',

                'mail_alert': {
                    'enabled': 'false',
                    'recipient': ''
                }
            },
            'packages': {
                'exclude': {
                    'always': [],
                    'on_major_update': []
                }
            },
            'services': {
                'restart': ''
            }
        }

        # Write config file
        with open(CONF, 'w') as file:
            yaml.dump(data, file, default_flow_style=False, sort_keys=False)


    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Return linupdate profile from config file
    #
    #-------------------------------------------------------------------------------------------------------------------
    def getProfile(self):
        # Open YAML config file:
        with open(CONF) as stream:
            try:
                # Read YAML and return profile
                data = yaml.safe_load(stream)
                return data['main']['profile']

            except yaml.YAMLError as exception:
                print(exception)


    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Return linupdate environment from config file
    #
    #-------------------------------------------------------------------------------------------------------------------
    def getEnvironment(self):
        # Open YAML config file:
        with open(CONF) as stream:
            try:
                # Read YAML and return environment
                data = yaml.safe_load(stream)
                return data['main']['environment']

            except yaml.YAMLError as exception:
                print(exception)


    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Print app logo
    #
    #-------------------------------------------------------------------------------------------------------------------
    def printLogo(self):
        space = '    '
        print(Fore.YELLOW)
        print(space + '.__  .__                        .___       __            ')
        print(space + '|  | |__| ____  __ ________   __| _/____ _/  |_  ____    ')
        print(space + '|  | |  |/    \|  |  \____ \ / __ |\__  \\   __\/ __ \   ')
        print(space + '|  |_|  |   |  \  |  /  |_> > /_/ | / __ \|  | \  ___/   ')
        print(space + '|____/__|___|  /____/|   __/\____ |(____  /__|  \___  >  ')
        print(space + '             \/      |__|        \/     \/          \/ \n')
        print(space + 'linupdate' + Style.RESET_ALL + ' - advanced package updater for linux distributions\n\n')


    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Print system and app summary
    #
    #-------------------------------------------------------------------------------------------------------------------
    def printSummary(self):
        mySystem = System()

        print(' Hostname:            ' + Fore.YELLOW + socket.gethostname() + Style.RESET_ALL)
        print(' OS:                  ' + Fore.YELLOW + mySystem.getOSName() + ' ' + mySystem.getOsVersion() + Style.RESET_ALL)
        print(' Kernel:              ' + Fore.YELLOW + mySystem.getKernel() + Style.RESET_ALL)
        print(' Virtualization:      ' + Fore.YELLOW + mySystem.getVirtualization() + Style.RESET_ALL)
        print(' Profile:             ' + Fore.YELLOW + self.getProfile() + Style.RESET_ALL)
        print(' Environment:         ' + Fore.YELLOW + self.getEnvironment() + Style.RESET_ALL)
        print(' Executed on:         ' + Fore.YELLOW + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + Style.RESET_ALL)
        print(' Executed by:         ' + Fore.YELLOW + getpass.getuser() + Style.RESET_ALL)
        # echo -ne " Execution method: "
        # if [ "$FROM_AGENT" == "1" ];then
        #     echo -e "            ${YELLOW}from linupdate agent${RESET}"
        # else
        #     if [ -t 0 ];then
        #         echo -e "            ${YELLOW}manual${RESET}"
        #     else
        #         echo -e "            ${YELLOW}automatic (no tty)${RESET}"
        #     fi
        # fi