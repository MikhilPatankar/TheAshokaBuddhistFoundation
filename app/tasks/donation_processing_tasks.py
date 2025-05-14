# app/tasks/donation_processing_tasks.py
from app.tasks.celery_app import celery_app
import logging
import time  # For example

logger = logging.getLogger(__name__)


# Example placeholder task for donation processing
@celery_app.task(
    name="process_new_donation", bind=True, max_retries=3, default_retry_delay=300
)  # 5 minutes
def process_new_donation_task(self, donation_id: int, payment_details: dict):
    logger.info(f"Task process_new_donation: Starting for donation_id {donation_id}")
    try:
        # Simulate interacting with a payment gateway or internal ledger
        logger.info(
            f"Processing payment for donation {donation_id} with details: {payment_details}"
        )
        time.sleep(10)  # Simulate work

        # Example: Update donation status in database (pseudo-code)
        # db_update_donation_status(donation_id, "processed")

        logger.info(
            f"Task process_new_donation: Successfully processed donation_id {donation_id}"
        )
        return {
            "status": "success",
            "donation_id": donation_id,
            "message": "Donation processed.",
        }
    except Exception as e:
        logger.error(
            f"Task process_new_donation: Error processing donation_id {donation_id}: {e}",
            exc_info=True,
        )
        # Retry the task if it's a transient error
        raise self.retry(exc=e)


# You can add more donation-related tasks here, for example:
@celery_app.task(name="send_donation_confirmation_email")
def send_donation_confirmation_email_task(
    user_email: str, donation_amount: float, donation_date: str
):
    from app.services.email_service import (
        send_email_async,
    )  # Local import to avoid circular deps if any
    import asyncio

    subject = "Thank You for Your Donation!"
    html_content = f"<p>Dear Donor,</p><p>Thank you for your generous donation of ${donation_amount} on {donation_date}.</p>"
    text_content = f"Dear Donor,\nThank you for your generous donation of ${donation_amount} on {donation_date}."

    logger.info(f"Task send_donation_confirmation_email: Sending to {user_email}")
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
            logger.info(f"Donation confirmation email sent to {user_email}")
        else:
            logger.warning(
                f"Failed to send donation confirmation email to {user_email}"
            )
            raise Exception("Email service reported failure for donation confirmation.")
    except Exception as e:
        logger.error(
            f"Error in send_donation_confirmation_email_task for {user_email}: {e}",
            exc_info=True,
        )
        # Decide if this task should be retried
        raise
