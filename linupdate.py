#!/usr/bin/python
# coding: utf-8

# Import constants
from constant import *

from App import App
from System import System
from colorama import Fore, Back, Style

# Exit if the user is not root
# if not System.isRoot():
#     print(Fore.YELLOW + 'Must be executed with sudo' + Style.RESET_ALL)
#     exit(1)

# Create lock file
App.setLock()

# Create base directories
App.initialize()

# Print Logo
App.printLogo()

System.checkSystem()










print('fin')