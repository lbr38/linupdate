# coding: utf-8

# Import classes
import sys
from src.controllers.App.App import App
from src.controllers.Mail import Mail

class Exit:
    #-----------------------------------------------------------------------------------------------
    #
    #   Clean and exit
    #
    #-----------------------------------------------------------------------------------------------
    def clean_exit(self, exit_code = 0, send_mail: bool = True, logfile: str = None):
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

        # Final exit
        sys.exit(exit_code)
