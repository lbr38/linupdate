# coding: utf-8

class StatusManager:
    _instance = None
    _status = None
    _saved_message = None
    _current_message = None  # To track the current message

    #-----------------------------------------------------------------------------------------------
    #
    #   Singleton pattern to ensure only one instance exists
    #
    #-----------------------------------------------------------------------------------------------
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StatusManager, cls).__new__(cls)
        return cls._instance
    
    #-----------------------------------------------------------------------------------------------
    #
    #   Set or update the status message
    #
    #-----------------------------------------------------------------------------------------------
    def set_status(self, status):
        self._status = status
    
    #-----------------------------------------------------------------------------------------------
    #
    #   Update the status message
    #
    #-----------------------------------------------------------------------------------------------
    def update(self, message: str):
        if self._status:
            self._status.update(message)
            self._current_message = message  # Save the current message

    #-----------------------------------------------------------------------------------------------
    #
    #   Save current status message
    #
    #-----------------------------------------------------------------------------------------------
    def save_current_message(self):
        """
        Save the current status message
        """
        if self._current_message:
            self._saved_message = self._current_message

    #-----------------------------------------------------------------------------------------------
    #
    #   Restore saved status message
    #
    #-----------------------------------------------------------------------------------------------
    def restore_saved_message(self):
        """
        Restore the previously saved status message
        """
        if self._saved_message and self._status:
            self._status.update(self._saved_message)
            self._current_message = self._saved_message
            self._saved_message = None  # Clear saved message after restore
    
    #-----------------------------------------------------------------------------------------------
    #
    #   Clear the status object reference
    #
    #-----------------------------------------------------------------------------------------------
    def clear(self):
        """Clear the status object reference"""
        self._status = None
        self._current_message = None
        self._saved_message = None


# Global instance - this ensures the same instance is used everywhere
status_manager = StatusManager()

#-----------------------------------------------------------------------------------------------
#
#   Update status message
#
#-----------------------------------------------------------------------------------------------
def update_status(message: str):
    status_manager.update(message)

#-----------------------------------------------------------------------------------------------
#
#   Save status message
#
#-----------------------------------------------------------------------------------------------
def save_status():
    """
    Save the current status message
    """
    status_manager.save_current_message()

#-----------------------------------------------------------------------------------------------
#
#   Restore status message
#
#-----------------------------------------------------------------------------------------------
def restore_status():
    """
    Restore the previously saved status message
    """
    status_manager.restore_saved_message()
