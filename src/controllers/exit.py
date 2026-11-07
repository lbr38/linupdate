# coding: utf-8

"""Clean exit: locks removal, mail report and optional reboot."""

# Import classes
import sys
from src.controllers.app.app import App
from src.controllers.mail import Mail
from src.controllers.system import System

class Exit:
    """Exit linupdate cleanly."""
    def clean_exit(self, exit_code = 0, send_mail: bool = False, reboot: bool = False, logfile: str = ''):
        """Clean and exit"""
        my_app = App()
        my_mail = Mail()

        # Remove all lock files
        try:
            my_app.remove_locks()
        except Exception as e:
            print(str(e))
            exit_code = 3

        # If send_mail is True, meaning a mail must be sent (if enabled)
        # It is not needed to send a mail if the script has just printed the --help for example
        if send_mail is True:
            # Define mail subject depending on exit code
            if exit_code == 0:
                subject = '✔ Packages update completed'

            if exit_code == 1:
                subject = '✕ Packages update failed'

            try:
                my_mail.send(subject, 'See report below or attached file.', logfile)
            except Exception:
                # If mail fails, exit with error code
                exit_code = 4

        # If reboot is True, reboot the system
        try:
            if reboot is True:
                print(' Rebooting...')
                System().reboot()
        except Exception as e:
            print(str(e))
            exit_code = 5

        # Final exit
        sys.exit(exit_code)
