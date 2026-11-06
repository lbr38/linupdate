# coding: utf-8

"""Console status message shared across the application."""

class StatusManager:
    """Singleton holding the current console status message."""
    _instance = None
    _status = None
    _saved_message = None
    _current_message = None  # To track the current message

    def __new__(cls):
        """Singleton pattern to ensure only one instance exists"""
        if cls._instance is None:
            cls._instance = super(StatusManager, cls).__new__(cls)
        return cls._instance

    def set_status(self, status):
        """Set or update the status message"""
        self._status = status

    def update(self, message: str):
        """Update the status message"""
        if self._status:
            self._status.update(message)
            self._current_message = message  # Save the current message

    def save_current_message(self):
        """
        Save the current status message
        """
        if self._current_message:
            self._saved_message = self._current_message

    def restore_saved_message(self):
        """
        Restore the previously saved status message
        """
        if self._saved_message and self._status:
            self._status.update(self._saved_message)
            self._current_message = self._saved_message
            self._saved_message = None  # Clear saved message after restore

    def clear(self):
        """Clear the status object reference"""
        self._status = None
        self._current_message = None
        self._saved_message = None


# Global instance - this ensures the same instance is used everywhere
status_manager = StatusManager()

def update_status(message: str):
    """Update status message"""
    status_manager.update(message)

def save_status():
    """
    Save the current status message
    """
    status_manager.save_current_message()

def restore_status():
    """
    Restore the previously saved status message
    """
    status_manager.restore_saved_message()
