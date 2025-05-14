from celery import Celery
from app.core.config import settings

# Ensure settings are loaded before Celery app is created
celery_app = Celery(
    "ashoka_tasks",
    broker=str(settings.CELERY_BROKER_URL),
    backend=str(settings.CELERY_RESULT_BACKEND_URL),
    include=[
        "app.tasks.email_tasks",
        "app.tasks.donation_processing_tasks",
    ],  # Auto-discover tasks
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",  # Set to your timezone
    enable_utc=True,
    # task_track_started=True, # Optional: if you want to track when tasks start
    # worker_prefetch_multiplier=1, # Can be tuned for I/O bound vs CPU bound tasks
    # task_acks_late=True, # If you want tasks to be acknowledged after completion/failure
)

# Optional: If you need to pass app context to tasks (e.g., for DB access, though it's better to pass IDs)
# class ContextTask(celery_app.Task):
#     def __call__(self, *args, **kwargs):
#         # Potentially set up DB session here if tasks need direct DB access
#         # Be cautious with session management in Celery tasks
#         return super().__call__(*args, **kwargs)
# celery_app.Task = ContextTask

if __name__ == "__main__":
    celery_app.start()
