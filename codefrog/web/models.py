import datetime
import logging
import os
from datetime import timedelta

from celery import chain, group
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.db.models import Count
from django.utils import timezone

from core.mixins import GithubMixin
from core.utils import date_range, run_shell_command
from ingest.models import Complexity
from engine.models import CodeChange

logger = logging.getLogger(__name__)


class Plan(models.Model):
    name = models.CharField(max_length=40)
    slug = models.CharField(max_length=40)
    has_trial_period = models.BooleanField(default=False)
    free_trial_days = models.IntegerField(default=14)

    def __str__(self):
        return f'{self.name} ({self.pk})'
