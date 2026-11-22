# coding: utf-8

"""Trigger files used to request actions from the linupdate service."""

# Import libraries
from pathlib import Path
from src.controllers.linupdate_exception import LinupdateException

class Trigger:
    """Create, remove and check trigger files."""
    def __init__(self) -> None:
        # In a root only directory, never in /tmp (writable by any user)
        self.trigger_path = '/opt/linupdate/tmp/trigger'

    def create(self, name) -> None:
        """Create trigger file"""
        try:
            if not Path(self.trigger_path + '.' + name).is_file():
                Path(self.trigger_path).parent.mkdir(parents=True, exist_ok=True)
                Path(self.trigger_path + '.' + name).touch()
        except Exception as e:
            raise LinupdateException('Could not create trigger file ' + self.trigger_path + '.' + name + ': ' + str(e)) from e


    def remove(self, name) -> None:
        """Remove trigger file"""
        try:
            if Path(self.trigger_path + '.' + name).is_file():
                Path(self.trigger_path + '.' + name).unlink()
        except Exception as e:
            raise LinupdateException('Could not remove trigger file ' + self.trigger_path + '.' + name + ': ' + str(e)) from e


    def exists(self, name) -> bool:
        """Return true if trigger file exists"""
        if Path(self.trigger_path + '.' + name).is_file():
            return True

        return False
