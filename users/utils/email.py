import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
 
class EmailManager():
    def __init__(self, from_email, to_emails, subject, html_content):
        
        """
        Initialize sending of Emails
        """
        self.from_email = from_email
        self.to_emails = to_emails
        self.subject = subject 
        self.html_content= html_content 
        
    def send_email(self):
        
        message = Mail(
            from_email= self.from_email,
            to_emails= self.to_emails,
            subject= self.subject,
            html_content= self.html_content
        )
        try:
            sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
            response = sg.send(message)
        except Exception as e:
            print(e)
                
        
        
        
    
        
    
         