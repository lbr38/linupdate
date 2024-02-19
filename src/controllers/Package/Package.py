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
            import apt

            # Create an instance of the apt cache
            self.aptcache = apt.Cache()
            self.aptcache.open(None)

        # If Redhat, import yum
        if (self.system.getOsFamily() == 'Redhat'):
            import yum

            # Create an instance of the yum base
            self.yumbase = yum.YumBase()



    def exclude(self):
        print(' Checking for package exclusions')

        # Clear package manager cache
        self.clearCache()

        # Get list of available packages
        self.getAvailablePackages()

        # Quit if there are no packages to update
        if (self.packagesToUpdateCount == 0):
            print(' No packages to update')
            return
        
        # Print the number of packages to update
        print(str(self.packagesToUpdateCount) + ' Packages to update:')

        # Print the list of packages to update
        for package in self.packagesToUpdateList:
            print(package.shortname)
        




    def getAvailablePackages(self):
        if (self.system.getOsFamily() == 'Debian'):
            # Get list of packages to update sorted by name
            self.packagesToUpdateList = sorted(self.aptcache.get_changes())

            # Count the number of packages to update
            self.packagesToUpdateCount = len(self.packagesToUpdateList)

      

            
    
    def clearCache(self):
        if (self.system.getOsFamily() == 'Debian'):
            self.aptcache.upgrade()
            return

        if (self.system.getOsFamily() == 'Redhat'):
            os.system('yum clean all')
            return
