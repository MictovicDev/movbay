import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailManager():
    def __init__(self, from_email, to_emails, subject, html_content):
        """
        Initialize sending of Emails
        """
        self.from_email = from_email
        self.to_emails = to_emails if isinstance(to_emails, list) else [to_emails]
        self.subject = subject 
        self.html_content = html_content

    def send_email(self):
        try:
            # Create a multipart message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = self.subject
            msg["From"] = self.from_email
            msg["To"] = ", ".join(self.to_emails)

            # Attach the HTML content
            part = MIMEText(self.html_content, "html")
            msg.attach(part)

            # Gmail SMTP setup
            smtp_server = "smtp.gmail.com"
            smtp_port = 587
            smtp_user = os.environ.get("GMAIL_USER")      # Your Gmail email
            smtp_pass = os.environ.get("GMAIL_PASSWORD")  # Your Gmail App Password

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(
                    self.from_email,
                    self.to_emails,
                    msg.as_string()
                )

            print("Email sent successfully.")

        except Exception as e:
            print(f"Email sending failed: {e}")
