# coding: utf-8

"""Trigger files used to request actions from the linupdate service."""

# Import libraries
from pathlib import Path
from src.controllers.linupdate_exception import LinupdateException

class Trigger:
    """Create, remove and check trigger files."""
    def __init__(self):
        self.trigger_path = '/tmp/linupdate.trigger'

    def create(self, name):
        """Create trigger file"""
        try:
            if not Path(self.trigger_path + '.' + name).is_file():
                Path(self.trigger_path + '.' + name).touch()
        except Exception as e:
            raise LinupdateException('Could not create trigger file ' + self.trigger_path + '.' + name + ': ' + str(e)) from e


    def remove(self, name):
        """Remove trigger file"""
        try:
            if Path(self.trigger_path + '.' + name).is_file():
                Path(self.trigger_path + '.' + name).unlink()
        except Exception as e:
            raise LinupdateException('Could not remove trigger file ' + self.trigger_path + '.' + name + ': ' + str(e)) from e


    def exists(self, name):
        """Return true if trigger file exists"""
        if Path(self.trigger_path + '.' + name).is_file():
            return True

        return False
