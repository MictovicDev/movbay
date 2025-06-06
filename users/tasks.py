from celery import shared_task
from users.utils.email import EmailManager
from payment.factories import ProcessorFactory

@shared_task
def send_welcome_email_async(from_email, to_emails, subject, html_content):
    sender = EmailManager(from_email, to_emails, subject, html_content)
    sender.send_email()
    
    
# @shared_task
# def create_virtual_account(data):
#     url = 'https://api.paystack.co/dedicated_account'
#     processor = ProcessorFactory.create_processor('paystack', url)
#     processor.create_dedicated_account(data)
    