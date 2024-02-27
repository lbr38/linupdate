#!/usr/bin/python
# coding: utf-8

# Import constants
from constant import *

# Import libraries
from colorama import Fore, Back, Style

# Import classes
from src.controllers.App import App
from src.controllers.System import System
from src.controllers.Module.Module import Module
from src.controllers.Package.Package import Package

# Instaciate classes
myApp     = App()
mySystem  = System()
myModule  = Module()
myPackage = Package()

# Exit if the user is not root
# if not System.isRoot():
#     print(Fore.YELLOW + 'Must be executed with sudo' + Style.RESET_ALL)
#     exit(1)

# Check if the system is supported
mySystem.check()

# Create lock file
myApp.setLock()

# Create base directories
myApp.initialize()

# Print Logo
myApp.printLogo()

# Generate config file if not exist
myApp.generateConf()

# TODO
# Params pre-check
# If --from-agent param is passed, then rewrite output log filename and make it hidden
# if echo "$@" | grep -q "\-\-from\-agent";then
#     REPORT=".${DATE_YMD}_${TIME_FULL}_linupdate_${HOSTNAME}-agent.log"
#     LOG="${LOGS_DIR}/${REPORT}"
# fi

# TODO
# Writing everything happening to the log file
# exec &> >(tee -a "$LOG")

# Print system & app summary
myApp.printSummary()

# Load modules
myModule.load()

# Execute pre-update modules
# execPreModules

# Execute packages update
myPackage.update()




































print('fin')