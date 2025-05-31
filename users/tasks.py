from celery import shared_task
from users.utils.email import EmailManager

@shared_task
def send_welcome_email_async(from_email, to_emails, subject, html_content):
    sender = EmailManager(from_email, to_emails, subject, html_content)
    sender.send_email()