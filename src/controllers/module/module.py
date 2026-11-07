# coding: utf-8

"""linupdate modules management: list, enable, disable, configure, load and hooks."""

# Import libraries
import os
import importlib
import shutil
from pathlib import Path
from colorama import Fore, Style

# Import classes
from src.controllers.app.config import Config
from src.controllers.exit import Exit
from src.controllers.linupdate_exception import LinupdateException

class Module:
    """Manage linupdate modules."""
    def __init__(self):
        self.config_controller = Config()
        self.exit_controller = Exit()
        self.loaded_modules = []

    def get_enabled(self):
        """Return list of enabled modules"""
        return self.config_controller.get_conf()['modules']['enabled']


    def list(self):
        """List available modules"""
        # List all modules
        print('Available modules:')

        for module in os.listdir('/opt/linupdate/src/controllers/module'):
            # Ignore cache files
            if module == '__pycache__':
                continue

            # Ignore non directories
            if not os.path.isdir('/opt/linupdate/src/controllers/module/' + module):
                continue

            print(Fore.GREEN + ' ▪ ' + module.lower())

        print(Style.RESET_ALL, end='\n')


    def enable(self, module):
        """Enable a module"""
        # Retrieve configuration
        configuration = self.config_controller.get_conf()

        # Loop through modules (remove duplicates)
        for mod in list(dict.fromkeys(module.split(','))):
            # Check if module exists
            if not self.exists(mod):
                raise LinupdateException('Module ' + mod + ' does not exist')

            # Continue if module is already enabled
            if mod not in configuration['modules']['enabled']:
                # Add enabled module in configuration
                self.config_controller.append_module(mod)

            # Copy module default configuration file if it does not exist
            if not Path('/etc/linupdate/modules/' + mod + '.yml').is_file():
                try:
                    shutil.copy2('/opt/linupdate/templates/modules/' + mod + '.template.yml', '/etc/linupdate/modules/' + mod + '.yml')
                except Exception as e:
                    raise LinupdateException('Could not generate module ' + mod + ' configuration file /etc/linupdate/modules/' + mod + '.yml: ' + str(e)) from e

            # Print enabled module
            print('Module ' + mod + Fore.GREEN + ' enabled' + Style.RESET_ALL)

        print('\n')


    def disable(self, module):
        """Disable a module"""
        # Retrieve configuration
        configuration = self.config_controller.get_conf()

        # Loop through modules (remove duplicates)
        for mod in list(dict.fromkeys(module.split(','))):
            # Check if module exists
            if not self.exists(mod):
                raise LinupdateException('Module ' + mod + ' does not exist')

            # Disable module
            if mod in configuration['modules']['enabled']:
                self.config_controller.remove_module(mod)

            # Print disabled modules
            print('Module ' + mod + Fore.YELLOW + ' disabled' + Style.RESET_ALL)

        print('\n')


    def configure(self, module, args):
        """Configure a module"""
        # Check if module exists
        if not self.exists(module):
            raise LinupdateException('Module ' + module + ' does not exist')

        # Convert module name tu uppercase first letter
        module_name = module.capitalize()

        # Import python module class
        module_import_path = importlib.import_module('src.controllers.module.' + module_name.lower() + '.' + module_name.lower())
        module_class = getattr(module_import_path, module_name)

        # Instanciate module and call module load method
        my_module = module_class()
        my_module.load()
        my_module.main(args)


    def exists(self, module):
        """Return True if module exists"""
        # Check if module class file exists
        if not os.path.exists('/opt/linupdate/src/controllers/module/' + module.lower() + '/' + module.lower() + '.py'):
            return False

        return True


    def load(self):
        """Load enabled modules"""
        # Retrieve configuration
        configuration = self.config_controller.get_conf()

        # Quit if no modules are enabled
        if not configuration['modules']['enabled']:
            return

        print('Loading modules:')

        # Loop through modules
        for module in configuration['modules']['enabled']:
            try:
                # Convert module name tu uppercase first letter
                module_name = module.capitalize()

                # Import python module class
                module_import_path = importlib.import_module('src.controllers.module.' + module_name.lower() + '.' + module_name.lower())
                module_class = getattr(module_import_path, module_name)

                # Instanciate module and call module load method
                my_module = module_class()
                my_module.load()

                print(Fore.GREEN + ' ✔ ' + Style.RESET_ALL + module + ' module loaded ')

                # Add module to the list of loaded modules
                self.loaded_modules.append(module)

            except Exception as e:
                raise LinupdateException('Could not load module ' + module + ': ' + str(e) + Style.RESET_ALL) from e


    def pre(self):
        """Execute modules pre-update actions (loaded modules only)"""
        for module in self.loaded_modules:
            try:
                print('\nExecuting ' + Fore.YELLOW + module + Style.RESET_ALL + ' pre-update actions:')
                # Convert module name to uppercase first letter
                module_name = module.capitalize()

                # Import python module class
                module_import_path = importlib.import_module('src.controllers.module.' + module_name.lower() + '.' + module_name.lower())
                module_class = getattr(module_import_path, module_name)

                # Instanciate module and call module pre method
                my_module = module_class()
                my_module.pre()

            except Exception as e:
                print(Fore.YELLOW + str(e) + Style.RESET_ALL)
                raise LinupdateException('Error while executing pre-update actions for module ' + module) from e


    def post(self, update_summary):
        """Execute modules post-update actions"""
        for module in self.loaded_modules:
            try:
                print('\nExecuting ' + Fore.YELLOW + module + Style.RESET_ALL + ' post-update actions:')
                # Convert module name to uppercase first letter
                module_name = module.capitalize()

                # Import python module class
                module_import_path = importlib.import_module('src.controllers.module.' + module_name.lower() + '.' + module_name.lower())
                module_class = getattr(module_import_path, module_name)

                # Instanciate module and call module post method
                my_module = module_class()
                my_module.post(update_summary)

            except Exception as e:
                print(Fore.YELLOW + str(e) + Style.RESET_ALL)
                raise LinupdateException('Error while executing post-update actions for module ' + module) from e
