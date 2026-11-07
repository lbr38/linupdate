# coding: utf-8

"""Miscellaneous helpers (JSON, ANSI codes, log cleanup, user confirmation)."""

# Import libraries
import json
import re
import tty
import termios
import sys
from colorama import Fore, Style

class Utils:
    """Miscellaneous helpers."""
    def is_json(self, json_string):
        """Return True if the string is a valid JSON"""
        try:
            json.loads(json_string)
        except json.decoder.JSONDecodeError:
            return False
        except ValueError:
            return False

        return True

    def remove_ansi(self, text):
        """Remove ANSI escape codes from a string"""
        try:
            ansi_escape = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')
            return ansi_escape.sub('', text)
        # If an exception occurs, simply return the original text as it is
        except Exception:
            return text

    def clean_log(self, text):
        """Clean log text"""
        # First, remove ANSI escape codes
        text = self.remove_ansi(text)

        # Replace double line breaks with single line breaks before '|' character (occurs mainly with apt logs)
        text = re.sub(r'\n\n\|', '\n|', text)

        return text

    def string_to_boolean(self, value: str):
        """Convert a string to a boolean"""
        if value in ('true', 'True'):
            return True

        return False

    def confirm(self, message):
        """Get user confirmation"""
        print(Fore.YELLOW + message + ' (y/n): ' + Style.RESET_ALL, end='', flush=True)

        # Save the terminal settings
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)

        try:
            # Set the terminal to raw mode to capture single keypress
            tty.setraw(sys.stdin.fileno())

            while True:
                ch = sys.stdin.read(1)
                if ch in ('y', 'Y'):
                    print('y')
                    return True

                return False
        finally:
            # Restore the terminal settings
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
