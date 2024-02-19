#!/usr/bin/python
# coding: utf-8

# Import constants
from constant import *
from colorama import Fore, Back, Style

from src.controllers.App import App
from src.controllers.System import System
from src.controllers.Module import Module

# Instaciate classes
myApp = App()
mySystem = System()
myModule = Module()

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

# Detect virtualization type
# if [ -f "/usr/sbin/virt-what" ];then
#     VIRT_TYPE=$(/usr/sbin/virt-what | tr '\n' ' ')
#     if [ -z "$VIRT_TYPE" ];then
#         VIRT_TYPE="Bare metal"
#     fi
# fi

# Reading configuration file
# App.getConf()

# Loading modules
# loadModules

# Execute pre-update modules
# execPreModules

myApp.printSummary()

# Load modules
# myModule.load()






































print('fin')