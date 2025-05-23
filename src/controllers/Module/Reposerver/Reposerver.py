# coding: utf-8

# Import classes
from src.controllers.Package.Package import Package
from src.controllers.Module.Reposerver.Config import Config as Config
from src.controllers.Module.Reposerver.Args import Args
from src.controllers.App.Trigger import Trigger

class Reposerver:
    def __init__(self):
        self.packageController = Package()
        self.configController = Config()
        self.argsController = Args()


    #-----------------------------------------------------------------------------------------------
    #
    #   Load Reposerver module
    #
    #-----------------------------------------------------------------------------------------------
    def load(self):
        # Note: no need of try / except block here, as it is already handled in the Module load() function

        # Generate config file if not exist
        self.configController.generate_conf()

        # Check config file
        self.configController.check_conf()


    #-----------------------------------------------------------------------------------------------
    #
    #   Execute pre-update actions
    #
    #-----------------------------------------------------------------------------------------------
    def pre(self):
        # Note: no need of try / except block here, as it is already handled in the Module pre() function

        # Retrieve profile configuration from reposerver
        self.configController.get_profile_packages_conf()

        # Retrieve profile repositories from reposerver
        self.configController.get_profile_repos()


    #-----------------------------------------------------------------------------------------------
    #
    #   Execute post-update actions
    #
    #-----------------------------------------------------------------------------------------------
    def post(self, updateSummary):
        # Note: no need of try / except block here, as it is already handled in the Module pre() function

        # Quit if there was no packages updates
        if updateSummary['update']['status'] == 'nothing-to-do':
            print('  ▪ Nothing to do as no packages have been updated')
            return

        # Generaly "*-release" packages on Redhat/CentOS are resetting .repo files. So it is better to retrieve them again from the reposerver
        self.configController.get_profile_repos()
        self.packageController.update_cache()

        # Trigger package-info sending
        Trigger().create('package-info')


    #-----------------------------------------------------------------------------------------------
    #
    #   Reposerver main function
    #
    #-----------------------------------------------------------------------------------------------
    def main(self, module_args):
        try:
            # Parse reposerver arguments
            self.argsController.parse(module_args)
        except Exception as e:
            raise Exception(str(e))
