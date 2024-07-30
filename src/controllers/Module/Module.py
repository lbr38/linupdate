# coding: utf-8

# Import libraries
import os
import importlib
import shutil
from pathlib import Path
from colorama import Fore, Style

# Import classes
from src.controllers.App.Config import Config
from src.controllers.Exit import Exit

class Module:
    def __init__(self):
        self.configController = Config()
        self.exitController = Exit()
        self.loadedModules = []

    #-----------------------------------------------------------------------------------------------
    #
    #   Return list of enabled modules
    #
    #-----------------------------------------------------------------------------------------------
    def getEnabled(self):
        return self.configController.get_conf()['modules']['enabled']


    #-----------------------------------------------------------------------------------------------
    #
    #   List available modules
    #
    #-----------------------------------------------------------------------------------------------
    def list(self):
        # List all modules
        print(' Available modules:')
        for module in os.listdir('/opt/linupdate/src/controllers/Module'):
            # Ignore cache files
            if module == '__pycache__':
                continue
            
            # Ignore non directories 
            if not os.path.isdir('/opt/linupdate/src/controllers/Module/' + module):
                continue

            print('  - ' + Fore.YELLOW + module.lower() + Style.RESET_ALL)


    #-----------------------------------------------------------------------------------------------
    #
    #   Enable a module
    #
    #-----------------------------------------------------------------------------------------------
    def enable(self, module):
        # Retrieve configuration
        configuration = self.configController.get_conf()

        # Loop through modules (remove duplicates)
        for mod in list(dict.fromkeys(module.split(','))):
            # Check if module exists
            if not self.exists(mod):
                raise Exception('Module ' + mod + ' does not exist')
            
            # Continue if module is already enabled
            if mod in configuration['modules']['enabled']:
                print(Fore.YELLOW + ' Module ' + mod + ' is already enabled' + Style.RESET_ALL)
                continue

            # Copy module default configuration file if it does not exist
            if not Path('/etc/linupdate/modules/' + mod + '.yml').is_file():
                try:
                    shutil.copy2('/opt/linupdate/templates/modules/' + mod + '.template.yml', '/etc/linupdate/modules/' + mod + '.yml')
                except Exception as e:
                    raise Exception('Could not generate module ' + mod + ' configuration file /etc/linupdate/modules/' + mod + '.yml: ' + str(e))

            # Add enabled module in configuration
            self.configController.append_module(mod)

            # Print enabled module
            print(Fore.GREEN + ' Module ' + mod + ' enabled' + Style.RESET_ALL)


    #-----------------------------------------------------------------------------------------------
    #
    #   Disable a module
    #
    #-----------------------------------------------------------------------------------------------
    def disable(self, module):
        # Retrieve configuration
        configuration = self.configController.get_conf()

        # Loop through modules (remove duplicates)
        for mod in list(dict.fromkeys(module.split(','))):
            # Check if module exists
            if not self.exists(mod):
                raise Exception('Module ' + mod + ' does not exist')
            
            # Continue if module is already disabled
            if mod not in configuration['modules']['enabled']:
                print(Fore.YELLOW + ' Module ' + mod + ' is already disabled' + Style.RESET_ALL)
                continue
        
            # Disable module
            self.configController.remove_module(mod)

            # Print disabled modules
            print(Fore.GREEN + ' Module ' + mod + ' disabled' + Style.RESET_ALL)


    #-----------------------------------------------------------------------------------------------
    #
    #   Configure a module
    #
    #-----------------------------------------------------------------------------------------------
    def configure(self, module, args):
        # Check if module exists
        if not self.exists(module):
            raise Exception('Module ' + module + ' does not exist')

        # Convert module name tu uppercase first letter
        moduleName = module.capitalize()

        # Import python module class
        moduleImportPath = importlib.import_module('src.controllers.Module.'+ moduleName + '.' + moduleName)
        moduleClass = getattr(moduleImportPath, moduleName)

        # Instanciate module and call module load method
        myModule = moduleClass()

        myModule.main(args)


    #-----------------------------------------------------------------------------------------------
    #
    #   Return True if module exists
    #
    #-----------------------------------------------------------------------------------------------
    def exists(self, module):
        # Check if module class file exists
        if not os.path.exists('/opt/linupdate/src/controllers/Module/' + module.capitalize() + '/' + module.capitalize() + '.py'):
            return False
        
        return True


    #-----------------------------------------------------------------------------------------------
    #
    #   Load enabled modules
    #
    #-----------------------------------------------------------------------------------------------
    def load(self):
        # Retrieve configuration
        configuration = self.configController.get_conf()

        # Quit if no modules are enabled
        if not configuration['modules']['enabled']:
            return
        
        print(' Loading modules')
    
        # Loop through modules
        for module in configuration['modules']['enabled']:
            try:
                # Convert module name tu uppercase first letter
                moduleName = module.capitalize()

                # Import python module class
                moduleImportPath = importlib.import_module('src.controllers.Module.'+ moduleName + '.' + moduleName)
                moduleClass = getattr(moduleImportPath, moduleName)

                # Instanciate module and call module load method
                myModule = moduleClass()
                myModule.load()

                print(Fore.GREEN + '  ✔ ' + Style.RESET_ALL + module + ' module loaded ')

                # Add module to the list of loaded modules
                self.loadedModules.append(module)

            except Exception as e:
                raise Exception('Could not load module ' + module + ': ' + str(e) + Style.RESET_ALL)


    #-----------------------------------------------------------------------------------------------
    #
    #   Execute modules pre-update actions (loaded modules only)
    #
    #-----------------------------------------------------------------------------------------------
    def pre(self):
        for module in self.loadedModules:
            try:
                print('\n Executing ' + Fore.YELLOW + module + Style.RESET_ALL + ' pre-update actions')
                # Convert module name to uppercase first letter
                moduleName = module.capitalize()

                # Import python module class
                moduleImportPath = importlib.import_module('src.controllers.Module.'+ moduleName + '.' + moduleName)
                moduleClass = getattr(moduleImportPath, moduleName)

                # Instanciate module and call module pre method
                myModule = moduleClass()
                myModule.pre()

            except Exception as e:
                print(Fore.YELLOW + str(e) + Style.RESET_ALL)
                raise Exception('Error while executing pre-update actions for module ' + module)


    #-----------------------------------------------------------------------------------------------
    #
    #   Execute modules post-update actions
    #
    #-----------------------------------------------------------------------------------------------
    def post(self, updateSummary):
        for module in self.loadedModules:
            try:
                print('\n Executing ' + Fore.YELLOW + module + Style.RESET_ALL + ' post-update actions')
                # Convert module name to uppercase first letter
                moduleName = module.capitalize()

                # Import python module class
                moduleImportPath = importlib.import_module('src.controllers.Module.'+ moduleName + '.' + moduleName)
                moduleClass = getattr(moduleImportPath, moduleName)

                # Instanciate module and call module post method
                myModule = moduleClass()
                myModule.post(updateSummary)

            except Exception as e:
                print(Fore.YELLOW + str(e) + Style.RESET_ALL)
                raise Exception('Error while executing post-update actions for module ' + module)
