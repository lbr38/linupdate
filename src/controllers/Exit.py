# coding: utf-8

# Import libraries
from colorama import Fore, Style

# Import classes
from src.controllers.App.App import App
from src.controllers.App.Config import Config
from src.controllers.Mail import Mail

class Exit:
    #-----------------------------------------------------------------------------------------------
    #
    #   Clean and exit
    #
    #-----------------------------------------------------------------------------------------------
    def clean_exit(self, exit_code = 0, send_mail: bool = True, logfile: str = None):
        my_app = App()
        my_config = Config()
        my_mail = Mail()

        if send_mail is True:
            # Try to get mail settings
            # It could fail if the config file is not found or if the 
            # mail section is not defined (e.g. first execution)
            # So if it fails to retrieve configuration, just don't send the mail
            try:
                mail_enabled = my_config.get_mail_enabled()
                mail_recipient = my_config.get_mail_recipient()
            except Exception as e:
                send_mail = False
                mail_enabled = False
                mail_recipient = None

        # Send mail unless send_mail is False 
        # (in some case mail is not needed, like when exiting at update confirmation)
        if send_mail is True:
            # Check if mail is enabled and recipient is set
            if (mail_enabled and mail_recipient):
                # Define mail subject depending on exit code
                if exit_code == 0:
                    subject = '[ OK ] Packages update completed'

                if exit_code == 1:
                    subject = '[ ERROR ] Packages update failed'

                print('\n Sending email report:')

                try:
                    my_mail.send(subject, 'See report below or attached file.', mail_recipient, logfile)
                    print('  ' + Fore.GREEN + '✔' + Style.RESET_ALL + ' Email sent')
                except Exception as e:
                    print('  ▪ ' + Fore.YELLOW + 'Error: ' + str(e) + Style.RESET_ALL)
                    # If mail fails, exit with error code
                    exit_code = 1

        # Remove lock
        my_app.remove_lock()

        # Final exit
        exit(exit_code)
