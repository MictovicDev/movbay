import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from django.template.loader import render_to_string

class EmailManager():
    def __init__(self, from_email, to_emails, subject, html_content=None, pdf_attachment=None, pdf_filename=None):
        """
        Initialize sending of Emails
        """
        self.from_email = from_email
        self.to_emails = to_emails if isinstance(to_emails, list) else [to_emails]
        self.subject = subject 
        self.html_content = html_content
        self.pdf_attachment = pdf_attachment
        self.pdf_filename = pdf_filename

    def send_email(self):
        try:
            # Create a multipart message
            msg = MIMEMultipart("mixed")
            msg["Subject"] = self.subject
            msg["From"] = self.from_email
            msg["To"] = ", ".join(self.to_emails)

            # If HTML content is provided, attach it
            if self.html_content:
                part = MIMEText(self.html_content, "html")
                msg.attach(part)

            # If PDF attachment is provided, attach it
            if self.pdf_attachment:
                pdf_part = MIMEApplication(self.pdf_attachment, _subtype="pdf")
                pdf_part.add_header(
                    "Content-Disposition", 
                    f"attachment; filename={self.pdf_filename or 'receipt.pdf'}"
                )
                msg.attach(pdf_part)

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
            return True

        except Exception as e:
            print(f"Email sending failed: {e}")
            return False
