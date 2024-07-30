# coding: utf-8

# Import libraries
import re
import smtplib
from email.message import EmailMessage
from email.headerregistry import Address

class Mail():
    #---------------------------------------------------------------------------------------------------
    #
    #   Send email
    #
    #---------------------------------------------------------------------------------------------------
    def send(self, subject: str, body: str, recipient: list, logfile = None):
        msg = EmailMessage()

        # If logfile is set, then clean it from ANSI escape codes
        if logfile:
            # Read logfile content
            with open(logfile, 'r') as f:
                content = f.read()

            # Get logfile real filename
            attachment = logfile.split('/')[-1]

            # Replace ANSI escape codes
            ansi_escape = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')
            content = ansi_escape.sub('', content)

        # Define email content and headers
        msg.set_content(body)
        msg['Subject'] = subject
        # msg['From'] = Address('Linupdate', 'noreply', socket.gethostname())
        msg['From'] = Address('Linupdate', 'noreply', 'example.com')
        msg['To'] = ','.join(recipient)

        # Add attachment
        bs = content.encode('utf-8')
        msg.add_attachment(bs, maintype='text', subtype='plain', filename=attachment)

        # Send the message via our own SMTP server
        s = smtplib.SMTP('localhost')
        s.send_message(msg)
        s.quit()
