# app/tasks/celery_app.py

# Apply eventlet monkey patching if eventlet is the chosen pool.
# This MUST be done BEFORE any modules that use standard library's socket, ssl, threading, etc. are imported.
# This includes Celery itself and potentially parts of your configuration loading if they import such modules.
try:
    # Check if '-P eventlet' or '--pool=eventlet' is in the command line arguments
    # This is a more robust way than checking environment variables set by Celery later.
    import sys

    worker_pool_is_eventlet = False
    for i, arg in enumerate(sys.argv):
        if arg == "-P" and i + 1 < len(sys.argv):
            if sys.argv[i + 1] == "eventlet":
                worker_pool_is_eventlet = True
                break
        elif arg.startswith("--pool="):
            if arg.split("=", 1)[1] == "eventlet":
                worker_pool_is_eventlet = True
                break

    if worker_pool_is_eventlet:
        import eventlet

        eventlet.monkey_patch()
        print("INFO: Eventlet monkey patch applied successfully.")
except ImportError:
    print("INFO: Eventlet not installed, skipping monkey patch.")
except Exception as e:
    print(f"WARNING: Error applying eventlet monkey patch: {e}")

from celery import Celery
from app.core.config import settings

# Ensure settings are loaded before Celery app is created
celery_app = Celery(
    "tasks",
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
