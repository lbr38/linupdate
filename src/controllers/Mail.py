# coding: utf-8

# Import libraries
import smtplib
import socket
from email.message import EmailMessage
from email.headerregistry import Address
from colorama import Fore, Style

# Import classes
from src.controllers.App.Config import Config
from src.controllers.App.Utils import Utils

class Mail():
    #-----------------------------------------------------------------------------------------------
    #
    #   Send email
    #
    #-----------------------------------------------------------------------------------------------
    def send(self, subject: str, body_content: str, attachment = None):
        try:
            configController = Config()
            msg = EmailMessage()
            attach_content = ''

            print('\n Sending email:', end=' ')

            # Get mail enabled
            mail_enabled = configController.get_mail_enabled()

            # If mail is not enabled, then quit
            if not mail_enabled:
                print(Fore.YELLOW + 'disabled' + Style.RESET_ALL)
                return

            # Get recipient(s) list
            recipient = configController.get_mail_recipient()

            # Get smtp host
            smtp_host = configController.get_mail_smtp_host()

            # Get smtp port
            smtp_port = configController.get_mail_smtp_port()

            # If attachment is set, then clean it from ANSI escape codes
            if attachment:
                # Read attachment content
                with open(attachment, 'r') as f:
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
            with open('/opt/linupdate/templates/mail/mail.template.html') as f:
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

            print(Fore.GREEN + 'sent' + Style.RESET_ALL)
        except Exception as e:
            print(Fore.YELLOW + str(e) + Style.RESET_ALL)
            raise Exception(str(e))
