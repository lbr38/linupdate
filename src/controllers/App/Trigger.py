# coding: utf-8

# Import libraries
from pathlib import Path

class Trigger:
    def __init__(self):
        self.trigger_path = '/tmp/linupdate.trigger'

    #-----------------------------------------------------------------------------------------------
    #
    #   Create trigger file
    #
    #-----------------------------------------------------------------------------------------------
    def create(self, name):
        try:
            if not Path(self.trigger_path + '.' + name).is_file():
                Path(self.trigger_path + '.' + name).touch()
        except Exception as e:
            raise Exception('Could not create trigger file ' + self.trigger_path + '.' + name + ': ' + str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   Remove trigger file
    #
    #-----------------------------------------------------------------------------------------------
    def remove(self, name):
        try:
            if Path(self.trigger_path + '.' + name).is_file():
                Path(self.trigger_path + '.' + name).unlink()
        except Exception as e:
            raise Exception('Could not remove trigger file ' + self.trigger_path + '.' + name + ': ' + str(e))


    #-----------------------------------------------------------------------------------------------
    #
    #   Return true if trigger file exists
    #
    #-----------------------------------------------------------------------------------------------
    def exists(self, name):
        if Path(self.trigger_path + '.' + name).is_file():
            return True

        return False
