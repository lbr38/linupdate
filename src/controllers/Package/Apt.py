# coding: utf-8

# Import libraries
import apt

from pprint import pprint

# Import classes
from src.controllers.System import System

class Apt:
    def __init__(self):
        self.system = System()

        # Create an instance of the apt cache
        self.aptcache = apt.Cache()
        # self.aptcache.update()
        self.aptcache.open(None)


    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Return list of available apt packages, sorted by name
    #
    #-------------------------------------------------------------------------------------------------------------------
    def getAvailablePackages(self):
        try:
            list = []

            # Simulate an upgrade
            self.aptcache.upgrade()            

            # Loop through all packages marked for upgrade
            for pkg in self.aptcache.get_changes():
                # If the package is upgradable, add it to the list of available packages
                if pkg.is_upgradable:
                    myPackage = {
                        'name': pkg.name,
                        'current_version': pkg.installed.version,
                        'available_version': pkg.candidate.version
                    }

                    list.append(myPackage)
            
            return list

        except Exception as e:
            print('Error while getting available packages: ' + str(e))


    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Update apt cache
    #
    #-------------------------------------------------------------------------------------------------------------------
    def updateCache(self):
        try:
            self.aptcache.upgrade()
        except Exception as e:
            print('Error while updating apt cache: ' + str(e))
