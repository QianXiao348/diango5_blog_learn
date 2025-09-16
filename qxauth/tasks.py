from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_email_async(subject, message, recipient_list, from_email):
    """
    异步发送邮件验证码
    """
    if from_email is None:
        from_email = settings.DEFAULT_FROM_EMAIL
    try:
        send_mail(
            subject,
            message,
            from_email,
            recipient_list,
            fail_silently=False,
        )
        print(f"Async email sent successfully to: {recipient_list}, subject: {subject}")
        return True
    except Exception as e:
        print(f"Async email failed to send to: {recipient_list}, subject: {subject}. Error: {e}")
        return False