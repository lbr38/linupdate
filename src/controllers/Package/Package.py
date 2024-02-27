# coding: utf-8

# https://github.com/excid3/python-apt/blob/master/doc/examples/inst.py

# Import libraries
import os
import array
import json

from pprint import pprint
from tabulate import tabulate

# Import classes
from src.controllers.System import System
from src.controllers.App import App

class Package:
    def __init__(self):
        self.systemController = System()
        self.appController = App()

        # Import libraries depending on the OS family

        # If Debian, import apt
        if (self.systemController.getOsFamily() == 'Debian'):
            from src.controllers.Package.Apt import Apt as PackageManager

        # If Redhat, import yum
        if (self.systemController.getOsFamily() == 'Redhat'):
            from src.controllers.Package.Yum import Yum

        self.myPackageManagerController = PackageManager()


    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Check for package exclusions
    #
    #-------------------------------------------------------------------------------------------------------------------
    def exclude(self):
        try:
            # Retrieve the list of packages to exclude from the config file
            configuration = self.appController.getConf()
            excludeAlways = configuration['packages']['exclude']['always']
            excludeOnMajorUpdate = configuration['packages']['exclude']['on_major_update']

            # Quit if the --ignore-exclude option is set
            # TODO

            # Quit if there is no packages to exclude (lists are empty)
            if not excludeAlways and not excludeOnMajorUpdate:
                print(' No packages to exclude')
                return

            # Exclude packages
            


        


            
            
            

        except Exception as e:
            print('Error while excluding packages: ' + str(e))
            return


    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Update packages
    #
    #-------------------------------------------------------------------------------------------------------------------
    def update(self):
        try:
            # First, clear package manager cache
            self.myPackageManagerController.updateCache()

            # Get a list of available packages
            self.packagesToUpdateList = self.myPackageManagerController.getAvailablePackages()
            self.packagesToUpdateCount = len(self.packagesToUpdateList)

            # Quit if there are no packages to update
            if (self.packagesToUpdateCount == 0):
                print(' No package to update')
                return

            # Check for package exclusions
            self.exclude()

            # Print the number of packages to update
            print(' ' + str(self.packagesToUpdateCount) + ' packages to update:')

            # Convert the list of packages to a table
            table = [[package['name'], package['current_version'], package['available_version']] for package in self.packagesToUpdateList]
            
            # Print the list of packages to update
            print(tabulate(table, headers=["Package", "Current version", "Available version"], tablefmt="simple"))
            # for package in self.packagesToUpdateList:
            #     print(package['name'] + ' ' + package['current_version'] + ' -> ' + package['available_version'])
        
        except Exception as e:
            print('An error occured while updating packages: ' + str(e))
            return





      

            
    
   
