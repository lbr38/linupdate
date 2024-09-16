# coding: utf-8

# Import libraries
import json
import re

class Utils:
    #-----------------------------------------------------------------------------------------------
    #
    #   Return True if the string is a valid JSON
    #
    #-----------------------------------------------------------------------------------------------
    def is_json(self, jsonString):
        try:
            json.loads(jsonString)
        except json.decoder.JSONDecodeError:
            return False
        except ValueError as e:
            return False

        return True
    
    #-----------------------------------------------------------------------------------------------
    #
    #   Remove ANSI escape codes from a string
    #
    #-----------------------------------------------------------------------------------------------
    def remove_ansi(self, text):
        try:
            ansi_escape = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')
            return ansi_escape.sub('', text)
        # If an exception occurs, simply return the original text as it is
        except Exception as e:
            return text
