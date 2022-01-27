import logging
import os

import structlog
from celery import Celery
from celery.schedules import crontab
from celery.signals import setup_logging
from django.dispatch import receiver
from django_structlog.celery.steps import DjangoStructLogInitStep

logger = structlog.get_logger(__name__)


# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

app = Celery("codefrog")

# A step to initialize django-structlog
app.steps["worker"].add(DjangoStructLogInitStep)

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@setup_logging.connect
def receiver_setup_logging(
    loglevel, logfile, format, colorize, **kwargs
):  # pragma: no cover
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "structured_json": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processor": structlog.processors.JSONRenderer(),
                },
            },
            "handlers": {
                "console": {
                    "level": "INFO",
                    "class": "logging.StreamHandler",
                    "formatter": "structured_json",
                },
                "null": {
                    "level": "DEBUG",
                    "class": "logging.NullHandler",
                },
            },
            "root": {
                "level": "INFO",
                "handlers": [
                    "console",
                ],
            },
            "loggers": {
                # discard logs from...
                "faker": {
                    "level": "DEBUG",
                    "handlers": ["null"],
                    "propagate": False,
                },
            },
        }
    )

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.ExceptionPrettyPrinter(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=structlog.threadlocal.wrap_dict(dict),
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    logger.info("Starting setup_periodic_tasks")

    sender.conf.update(
        beat_schedule={
            "update_all_projects": {
                "task": "core.tasks.update_all_projects",
                "schedule": crontab(hour="*/3", minute="0"),  # every three hours
            },
        }
    )

    logger.info("Finished setup_periodic_tasks")


@app.task(bind=True)
def debug_task(self):
    print("Request: {0!r}".format(self.request))
