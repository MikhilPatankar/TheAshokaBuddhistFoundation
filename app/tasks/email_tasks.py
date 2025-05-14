# app/tasks/email_tasks.py
import asyncio
from app.tasks.celery_app import celery_app
from app.services.email_service import send_email_async
from app.core.config import settings  # For logging and checking environment
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name="send_registration_email", bind=True, max_retries=3, default_retry_delay=60)
def send_registration_email_task(self, user_email: str, username: str):
    subject = "Welcome to The Ashoka Buddhist Foundation!"
    # In a real application, you'd use Jinja2 templates for emails
    # For example, render_template("emails/registration.html", username=username)
    html_content = f"""
    <html>
        <head>
            <style>
                body {{ font-family: sans-serif; margin: 20px; color: #333; }}
                h1 {{ color: #4CAF50; }}
                p {{ line-height: 1.6; }}
                .footer {{ font-size: 0.9em; color: #777; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <h1>Welcome, {username}!</h1>
            <p>Thank you for registering at The Ashoka Buddhist Foundation.</p>
            <p>We are delighted to have you as part of our community focused on promoting peace, wisdom, and compassion through the teachings of Buddhism.</p>
            <p>Explore our resources, join discussions, and participate in events to deepen your understanding and practice.</p>
            <p>If you have any questions or need assistance, please do not hesitate to contact us.</p>
            <br>
            <p>Warm regards,</p>
            <p>The Ashoka Buddhist Foundation Team</p>
            <div class="footer">
                <p>&copy; {{{{ now().year }}}} The Ashoka Buddhist Foundation. All rights reserved.</p>
                <p><a href="{settings.WEB_APP_BASE_URL}">Visit our website</a></p>
            </div>
        </body>
    </html>
    """  # Note: Jinja2 syntax like {{ now().year }} won't work here directly.
    # It's better to render this with a proper template engine before passing to the email service.
    # For now, let's make it simple:
    html_content = html_content.replace(
        "{{{{ now().year }}}}",
        str(asyncio.run(asyncio.sleep(0, result=__import__("datetime").datetime.now().year))),
    )

    text_content = f"""
    Welcome, {username}!

    Thank you for registering at The Ashoka Buddhist Foundation.
    We are delighted to have you as part of our community focused on promoting peace, wisdom, and compassion through the teachings of Buddhism.

    Explore our resources, join discussions, and participate in events to deepen your understanding and practice.

    If you have any questions or need assistance, please do not hesitate to contact us.

    Warm regards,
    The Ashoka Buddhist Foundation Team

    ---
    Visit our website: {settings.WEB_APP_BASE_URL}
    """

    logger.info(
        f"Task send_registration_email: Attempting to send to {user_email} for user {username}."
    )

    try:
        # Call the async function from the synchronous Celery task
        # asyncio.run() is suitable here as each task execution is independent.
        success = asyncio.run(
            send_email_async(
                to_email=user_email,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
            )
        )
        if success:
            logger.info(
                f"Task send_registration_email: Email for {user_email} sent (or simulated) successfully."
            )
        else:
            logger.warning(
                f"Task send_registration_email: Email service reported failure for {user_email}. Retrying if applicable."
            )
            # Raise an exception to trigger Celery's retry mechanism
            raise Exception("Email sending reported as failed by the service.")
    except Exception as e:
        logger.error(
            f"Task send_registration_email: Error sending email to {user_email}: {e}",
            exc_info=True,
        )
        try:
            # self.retry will re-raise the exception if max_retries is exceeded,
            # or raise MaxRetriesExceededError.
            raise self.retry(exc=e)
        except Exception as retry_exc:  # Catch if retry itself fails or max retries exceeded
            logger.error(
                f"Task send_registration_email: Failed to retry or max retries exceeded for {user_email}. Error: {retry_exc}"
            )
            # Potentially log to a dead-letter queue or notify admins
            # For now, just log the final failure.


# Example of another task (you can add more as needed)
@celery_app.task(
    name="send_password_reset_email", bind=True, max_retries=3, default_retry_delay=120
)
def send_password_reset_email_task(self, user_email: str, username: str, reset_token: str):
    subject = "Password Reset Request - The Ashoka Buddhist Foundation"
    # Ensure this route exists
    reset_link = f"{settings.WEB_APP_BASE_URL}/auth/reset-password?token={reset_token}"
    html_content = f"""
    <p>Hello {username},</p>
    <p>You requested a password reset. Please click the link below to set a new password:</p>
    <p><a href='{reset_link}'>{reset_link}</a></p>
    <p>If you did not request this, please ignore this email.</p>
    <p>This link will expire in 1 hour.</p>
    <br><p>Regards,<br>The Ashoka Buddhist Foundation Team</p>
    """
    text_content = f"""
    Hello {username},

    You requested a password reset. Please use the following link to set a new password:
    {reset_link}

    If you did not request this, please ignore this email.
    This link will expire in 1 hour.

    Regards,
    The Ashoka Buddhist Foundation Team
    """
    logger.info(f"Task send_password_reset_email: Attempting to send to {user_email}.")
    try:
        success = asyncio.run(
            send_email_async(
                to_email=user_email,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
            )
        )
        if success:
            logger.info(
                f"Task send_password_reset_email: Email for {user_email} sent successfully."
            )
        else:
            logger.warning(
                f"Task send_password_reset_email: Email service reported failure for {user_email}."
            )
            raise Exception("Password reset email sending reported as failed.")
    except Exception as e:
        logger.error(
            f"Task send_password_reset_email: Error sending email to {user_email}: {e}",
            exc_info=True,
        )
        raise self.retry(exc=e)
