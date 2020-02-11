import logging
import os

from celery import Celery
from celery.schedules import crontab

logger = logging.getLogger(__name__)


# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

app = Celery('codefrog')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    logger.info("Starting setup_periodic_tasks")

    sender.conf.update(
        beat_schedule={
            'update_all_projects': {
                'task': 'core.tasks.update_all_projects',
                'schedule': crontab(hour='*', minute='0'),
            },
        })

    logger.info("Finished setup_periodic_tasks")


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
