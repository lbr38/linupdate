# coding: utf-8

# Import libraries
import re
import smtplib
import socket
from email.message import EmailMessage
from email.headerregistry import Address

class Mail():
    #-----------------------------------------------------------------------------------------------
    #
    #   Send email
    #
    #-----------------------------------------------------------------------------------------------
    def send(self, subject: str, body_content: str, recipient: list, logfile = None):
        msg = EmailMessage()

        # If logfile is set, then clean it from ANSI escape codes
        if logfile:
            # Read logfile content
            with open(logfile, 'r') as f:
                attach_content = f.read()

            # Get logfile real filename
            attachment = logfile.split('/')[-1]

            # Replace ANSI escape codes
            ansi_escape = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')
            attach_content = ansi_escape.sub('', attach_content)

        # Define email content and headers
        msg['Subject'] = subject
        # debug only
        # msg['From'] = Address('Linupdate', 'noreply', 'example.com')
        msg['From'] = Address('Linupdate', 'noreply', socket.gethostname())
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
        if attach_content:
            bs = attach_content.encode('utf-8')
            msg.add_attachment(bs, maintype='text', subtype='plain', filename=attachment)

        # Send the message via our own SMTP server
        s = smtplib.SMTP('localhost')
        s.send_message(msg)
        s.quit()

