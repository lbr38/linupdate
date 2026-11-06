# coding: utf-8

"""Reposerver module entry point: load, pre/post update hooks and configuration."""

# Import classes
from src.controllers.package.package import Package
from src.controllers.module.reposerver.config import Config
from src.controllers.module.reposerver.args import Args
from src.controllers.app.trigger import Trigger
from src.controllers.linupdate_exception import LinupdateException

class Reposerver:
    """Reposerver module."""
    def __init__(self):
        self.package_controller = Package()
        self.config_controller = Config()
        self.args_controller = Args()


    def load(self):
        """Load Reposerver module"""
        # Note: no need of try / except block here, as it is already handled in the Module load() function

        # Generate config file if not exist
        self.config_controller.generate_conf()

        # Check config file
        self.config_controller.check_conf()


    def pre(self):
        """Execute pre-update actions"""
        # Note: no need of try / except block here, as it is already handled in the Module pre() function

        # Retrieve profile configuration from reposerver
        self.config_controller.get_profile_packages_conf()

        # Retrieve profile repositories from reposerver
        self.config_controller.get_profile_repos()


    def post(self, update_summary):
        """Execute post-update actions"""
        # Note: no need of try / except block here, as it is already handled in the Module pre() function

        # Quit if there was no packages updates
        if update_summary['update']['status'] == 'nothing-to-do':
            print(' ▪ Nothing to do as no packages have been updated')
            return

        # Generaly "*-release" packages on Redhat/CentOS are resetting .repo files. So it is better to retrieve them again from the reposerver
        self.config_controller.get_profile_repos()

        # Trigger package-info sending
        Trigger().create('package-info')


    def main(self, module_args):
        """Reposerver main function"""
        try:
            # Parse reposerver arguments
            self.args_controller.parse(module_args)
        except Exception as e:
            raise LinupdateException(str(e)) from e
