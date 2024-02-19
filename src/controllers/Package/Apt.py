# coding: utf-8

# Import libraries
import apt
import os

# Import classes
from src.controllers.System import System

class Apt:
    def __init__(self):
        self.system = System()

        # Create an instance of the apt cache
        self.aptcache = apt.Cache()
        self.aptcache.open(None)



    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Return list of available apt packages, sorted by name
    #
    #-------------------------------------------------------------------------------------------------------------------
    def getAvailablePackages(self):
        return sorted(self.aptcache.get_changes())



    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Clear apt cache
    #
    #-------------------------------------------------------------------------------------------------------------------
    def clearCache(self):
        self.aptcache.upgrade()
        return
