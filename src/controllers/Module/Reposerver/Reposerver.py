# coding: utf-8

# Import classes
from src.controllers.Module.Reposerver.Config import Config as ReposerverConfig
from src.controllers.Module.Reposerver.Status import Status
from src.controllers.Module.Reposerver.Args import Args

class Reposerver:
    def __init__(self):
        self.reposerverConfigController = ReposerverConfig()
        self.statusController = Status()
        self.argsController = Args()


    #-----------------------------------------------------------------------------------------------
    #
    #   Load Reposerver module
    #
    #-----------------------------------------------------------------------------------------------
    def load(self):
        # Note: no need of try / except block here, as it is already handled in the Module load() function

        # Generate config file if not exist
        self.reposerverConfigController.generate_conf()

        # Check config file
        self.reposerverConfigController.check_conf()


    #-----------------------------------------------------------------------------------------------
    #
    #   Execute pre-update actions
    #
    #-----------------------------------------------------------------------------------------------
    def pre(self):
        # Note: no need of try / except block here, as it is already handled in the Module pre() function

        # Retrieve global configuration from reposerver
        self.reposerverConfigController.get_reposerver_conf()

        # Retrieve profile configuration from reposerver
        self.reposerverConfigController.get_profile_packages_conf()

        # Retrieve profile repositories from reposerver
        self.reposerverConfigController.get_profile_repos()


    #-----------------------------------------------------------------------------------------------
    #
    #   Execute post-update actions
    #
    #-----------------------------------------------------------------------------------------------
    def post(self, updateSummary):
        # Note: no need of try / except block here, as it is already handled in the Module pre() function

        # Quit if there was no packages updates
        if updateSummary['update']['success']['count'] == 0:
            print('  ▪ Nothing to do as no packages have been updated')
            return

        # Generaly "*-release" packages on Redhat/CentOS reset .repo files. If a package of this type has been updated then we update the repos configuration from the repo server (profiles)
        # If a package named *-release is present in the updated packages list
        for package in updateSummary['update']['success']['packages']:
            if package.endswith('-release'):
                # Update repositories
                self.reposerverConfigController.get_profile_repos()
                break

        # Send last 4 packages history entries to the reposerver
        self.statusController.sendFullHistory(4)


    #-----------------------------------------------------------------------------------------------
    #
    #   Reposerver main function
    #
    #-----------------------------------------------------------------------------------------------
    def main(self, module_args):
        try:
            # Generate config file if not exist
            self.reposerverConfigController.generate_conf()
            # Check config file
            self.reposerverConfigController.check_conf()
            # Parse reposerver arguments
            self.argsController.parse(module_args)
        except Exception as e:
            raise Exception(str(e))
