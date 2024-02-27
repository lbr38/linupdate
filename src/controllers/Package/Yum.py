# coding: utf-8

# Import libraries
import yum
import os

# Import classes
from src.controllers.System import System

class Yum:
    def __init__(self):
        self.system = System()

        # Create an instance of the yum package manager
        self.yumbase = yum.YumBase()


    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Return list of available yum packages, sorted by name
    #
    #-------------------------------------------------------------------------------------------------------------------
    def getAvailablePackages(self):
        # Get list of packages to update sorted by name
        # TODO
        return 



    #-------------------------------------------------------------------------------------------------------------------
    #
    #   Clear yum cache
    #
    #-------------------------------------------------------------------------------------------------------------------
    def clearCache(self):
        # TODO
        os.system('yum clean all')
        return