# coding: utf-8

import logging
import sys

class StreamToLogger:
    def __init__(self, log_file_path, level=logging.INFO):
        self.logger = logging.getLogger("StreamToLogger")
        self.level = level
        self.buffer = ''  # Used to accumulate partial messages

        # Clean existing handlers to avoid accumulation
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)

        # Save original streams BEFORE redirection
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

        # Logger configuration
        self.logger.setLevel(level)
        formatter = logging.Formatter('%(message)s')

        # File handler
        self.file_handler = logging.FileHandler(log_file_path)
        self.file_handler.setFormatter(formatter)
        self.logger.addHandler(self.file_handler)

        # Console handler (uses original streams)
        self.console_handler = logging.StreamHandler(self.original_stdout)
        self.console_handler.setFormatter(formatter)
        self.logger.addHandler(self.console_handler)

    def write(self, message):
        # Accumulate partial messages
        self.buffer += message
        while '\n' in self.buffer:  # If a newline is detected
            line, self.buffer = self.buffer.split('\n', 1)
            self.logger.log(self.level, line)  # Send the line to the logger

    def flush(self):
        if self.buffer:  # If the buffer still contains data
            self.logger.log(self.level, self.buffer)  # Send the remaining content
            self.buffer = ''

    def __enter__(self):
        # Perform redirection only when entering the context
        sys.stdout = self
        sys.stderr = self
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Flush the buffer if data remains
        self.flush()
        
        # Restore standard streams
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        
        # Properly close handlers to avoid resource leaks
        self.file_handler.close()
        self.console_handler.close()
        
        # Do not log SystemExit and KeyboardInterrupt which are normal exits
        # if exc_type is not None and exc_type not in (SystemExit, KeyboardInterrupt):
        #     self.logger.error("Exception occurred", exc_info=(exc_type, exc_value, traceback))
