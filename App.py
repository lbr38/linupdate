# coding: utf-8

from constant import *
from pathlib import Path
from colorama import Fore, Back, Style

class App:

    #
    # Return current version of the application
    #
    def getVersion():
        file = open(ROOT + '/version', 'r')
        version = file.read()

        return version

    #
    # Create lock file
    #
    def setLock():
        Path('/tmp/linupdate.lock').touch()

    #
    # Create base directories
    #
    def initialize():
        Path(ROOT).mkdir(parents=True, exist_ok=True)
        Path(ETC_DIR).mkdir(parents=True, exist_ok=True)
        Path(MODULES_CONF_DIR).mkdir(parents=True, exist_ok=True)
        Path(MODULES_DIR).mkdir(parents=True, exist_ok=True)
        Path(MODULES_ENABLED_DIR).mkdir(parents=True, exist_ok=True)
        Path(AGENTS_ENABLED_DIR).mkdir(parents=True, exist_ok=True)
        Path(SERVICE_DIR).mkdir(parents=True, exist_ok=True)

        # Set permissions
        Path(ROOT).chmod(0o750)
        Path(SRC_DIR).chmod(0o750)
        Path(ETC_DIR).chmod(0o750)
        Path(MODULES_CONF_DIR).chmod(0o750)
        Path(MODULES_DIR).chmod(0o750)
        Path(MODULES_ENABLED_DIR).chmod(0o750)
        Path(AGENTS_ENABLED_DIR).chmod(0o750)
        Path(SERVICE_DIR).chmod(0o750)

        # Check if the .src directory is empty
        if not len(list(Path(SRC_DIR).rglob('*'))):
            print(Fore.YELLOW + 'Linupdate core files are missing. You might reinstall linupdate.' + Style.RESET_ALL)
            exit(1)





        

    #
    # Print app logo
    #
    def printLogo():
        space = '    '
        print(Fore.YELLOW)
        print(space + '.__  .__                        .___       __')
        print(space + '|  | |__| ____  __ ________   __| _/____ _/  |_  ____')
        print(space + '|  | |  |/    \|  |  \____ \ / __ |\__  \\   __\/ __ \ ')
        print(space + '|  |_|  |   |  \  |  /  |_> > /_/ | / __ \|  | \  ___/')
        print(space + '|____/__|___|  /____/|   __/\____ |(____  /__|  \___  >')
        print(space + '             \/      |__|        \/     \/          \/ \n')
        print(space + 'linupdate' + Style.RESET_ALL + ' - advanced package updater for linux distributions\n\n')


