# coding: utf-8

# https://github.com/excid3/python-apt/blob/master/doc/examples/inst.py

# Import libraries
import os

# Import classes
from src.controllers.System import System

class Package:
    def __init__(self):
        self.system = System()

        # Import libraries depending on the OS family

        # If Debian, import apt
        if (self.system.getOsFamily() == 'Debian'):
            from src.controllers.Package.Apt import Apt as PackageManager

        # If Redhat, import yum
        if (self.system.getOsFamily() == 'Redhat'):
            from src.controllers.Package.Yum import Yum

        self.myPackageManager = PackageManager()


    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Check for package exclusions
    #
    #-------------------------------------------------------------------------------------------------------------------
    def exclude(self):
        print(' Checking for package exclusions')

        try:
            # Clear package manager cache
            self.myPackageManager.clearCache()

            # Get list of available packages
            packagesToUpdateList = self.myPackageManager.getAvailablePackages()
            packagesToUpdateCount = len(packagesToUpdateList)

            # Quit if there are no packages to update
            if (packagesToUpdateCount == 0):
                print(' No packages to update')
                return
            
            # Print the number of packages to update
            print(str(packagesToUpdateCount) + ' Packages to update:')

            # Print the list of packages to update
            for package in packagesToUpdateList:
                print(package.shortname)

        except Exception as e:
            print('Error: ' + str(e))
            return





      

            
    
   
