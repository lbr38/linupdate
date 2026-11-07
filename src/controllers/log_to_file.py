# coding: utf-8

"""Context manager copying stdout and exceptions to a log file."""

import traceback
import sys

# https://stackoverflow.com/a/57008553

# Context manager that copies stdout and any exceptions to a log file
class LogToFile:
    """Copy stdout and exceptions to a log file while still printing them."""
    def __init__(self, filename):
        # Closed in __exit__
        self.file = open(filename, 'w', encoding='utf-8') # pylint: disable=consider-using-with
        self.stdout = sys.stdout

    def __enter__(self):
        sys.stdout = self

    def __exit__(self, exc_type, exc_value, tb):
        sys.stdout = self.stdout
        if exc_type is not None:
            self.file.write(traceback.format_exc())
        self.file.close()

    def write(self, data):
        """Write data to the log file and to the original stdout."""
        self.file.write(data)
        self.stdout.write(data)
        self.file.flush()

    def flush(self):
        """Flush the log file and the original stdout."""
        self.file.flush()
        self.stdout.flush()

    def get_content(self):
        """Return the original stdout."""
        return self.stdout
