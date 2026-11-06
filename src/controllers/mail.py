# coding: utf-8

"""Mail report sending."""

# Import libraries
import smtplib
import socket
from email.message import EmailMessage
from email.headerregistry import Address
from colorama import Fore, Style

# Import classes
from src.controllers.app.config import Config
from src.controllers.app.utils import Utils
from src.controllers.status import update_status
from src.controllers.linupdate_exception import LinupdateException

class Mail():
    """Send the update report by mail."""
    def send(self, subject: str, body_content: str, attachment = None):
        """Send email"""
        try:
            config_controller = Config()
            msg = EmailMessage()
            attach_content = ''

            # Get mail enabled
            mail_enabled = config_controller.get_mail_enabled()

            # If mail is not enabled, then quit
            if not mail_enabled:
                return

            update_status('Sending email...')

            # Get recipient(s) list
            recipient = config_controller.get_mail_recipient()

            # Get smtp host
            smtp_host = config_controller.get_mail_smtp_host()

            # Get smtp port
            smtp_port = config_controller.get_mail_smtp_port()

            # If attachment is set, then clean it from ANSI escape codes
            if attachment:
                # Read attachment content
                with open(attachment, 'r', encoding='utf-8') as f:
                    # Remove ANSI escape codes
                    attach_content = Utils().remove_ansi(f.read())

                # Get attachment real filename
                attachment = attachment.split('/')[-1]

            # Define email content and headers
            msg['Subject'] = subject
            # debug only
            # msg['From'] = Address('Linupdate', 'noreply', 'example.com')
            msg['From'] = Address('Linupdate', 'noreply', socket.getfqdn())
            msg['To'] = ','.join(recipient)

            # Retrieve HTML mail template
            with open('/opt/linupdate/templates/mail/mail.template.html', encoding='utf-8') as f:
                template = f.read()
                # Replace values in template
                template = template.replace('__CONTENT__', body_content)
                template = template.replace('__PRE_CONTENT__', attach_content)

            # Add HTML body
            msg.add_alternative(template, subtype='html')

            # Add attachment if there is
            if attach_content and attach_content != '':
                bs = attach_content.encode('utf-8')
                msg.add_attachment(bs, maintype='text', subtype='plain', filename=attachment)

            # Send the message via SMTP server
            s = smtplib.SMTP(smtp_host, smtp_port)
            s.send_message(msg)
            s.quit()

        except Exception as e:
            print(Fore.YELLOW + str(e) + Style.RESET_ALL)
            raise LinupdateException(' An error occurred while sending email: ' + str(e)) from e
