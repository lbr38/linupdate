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
        except ValueError:
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
        except Exception:
            return text

    #-----------------------------------------------------------------------------------------------
    #
    #   Clean log text
    #
    #-----------------------------------------------------------------------------------------------
    def clean_log(self, text):
        # First, remove ANSI escape codes
        text = self.remove_ansi(text)

        # Replace double line breaks with single line breaks before '|' character (occurs mainly with apt logs)
        text = re.sub(r'\n\n \|', '\n |', text)

        # Remove leading and trailing whitespaces
        text = text.strip()

        return text

    #-----------------------------------------------------------------------------------------------
    #
    #   Convert a string to a boolean
    #
    #-----------------------------------------------------------------------------------------------
    def stringToBoolean(self, value: str):
        if value == 'true' or value == 'True':
            return True

        return False
