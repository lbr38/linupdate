# coding: utf-8

# Import constants
from constant import *

# Import libraries
from colorama import Fore, Back, Style
import os

class Module:
    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Load enabled modules
    #
    #-------------------------------------------------------------------------------------------------------------------
    def load(self):
        # Quit if enabled modules dir is empty
        if not os.listdir(MODULES_ENABLED_DIR):
            print(Fore.YELLOW + '\n Could not load modules: modules directory is empty' + Style.RESET_ALL)
            return
        
        print('\n Loading modules')
    
        # Loop through modules
        for module in os.listdir(MODULES_ENABLED_DIR):
            # Get module name without extension
            module = module.split('.')[0]

            # Convert module name tu uppercase first letter
            module = module.capitalize()

            # Import python module class
            exec('from src.controllers.Module.' + module + ' import ' + module)

            # Instanciate module and call module load method
            myModule = eval(module)()
            myModule.load()
