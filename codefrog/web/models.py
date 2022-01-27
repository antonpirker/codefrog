from datetime import timedelta

import structlog
from django.conf import settings
from django.core.mail import send_mail
from django.db import models
from django.utils import timezone

logger = structlog.get_logger(__name__)


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    github_app_installation_refid = models.IntegerField(null=True)

    fastspring_subscription_refid = models.CharField(
        max_length=100, blank=True, default=""
    )
    fastspring_account_refid = models.CharField(max_length=100, blank=True, default="")

    newly_registered = models.BooleanField(default=True)

    plan = models.ForeignKey(
        "web.Plan",
        on_delete=models.SET_NULL,
        db_index=True,
        null=True,
    )

    date_joined = models.DateTimeField(default=timezone.now, null=False)

    @property
    def plan_expiration_date(self):
        return self.date_joined + timedelta(days=self.plan.free_trial_days)

    @property
    def plan_has_expired(self):
        if not self.plan.has_trial_period:
            return False

        if self.plan_expiration_date >= timezone.now():
            return False

        return True

    @property
    def plan_name_and_status(self):
        plan_name = f"{ self.plan.name } Plan"

        if self.plan_has_expired:
            plan_name = "%s (Free trial expired: %s)" % (
                plan_name,
                self.plan_expiration_date.strftime("%B %d, %Y"),
            )
        else:
            plan_name = "%s (Free trial period until: %s)" % (
                plan_name,
                self.plan_expiration_date.strftime("%B %d, %Y"),
            )

        return plan_name

    def __str__(self):
        return f"{self.user.username} ({self.pk})"


class Plan(models.Model):
    name = models.CharField(max_length=40)
    slug = models.CharField(max_length=40)
    has_trial_period = models.BooleanField(default=False)
    free_trial_days = models.IntegerField(default=14)

    def __str__(self):
        return f"{self.name} ({self.pk})"


class Usage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_index=True,
        null=True,
    )
    project = models.ForeignKey(
        "core.Project",
        on_delete=models.CASCADE,
        db_index=True,
        null=True,
    )
    timestamp = models.DateTimeField(db_index=True)
    action = models.CharField(max_length=100, blank=False, db_index=True)


class Message(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_index=True,
        null=True,
    )
    timestamp = models.DateTimeField(db_index=True)
    message = models.TextField()
    url = models.CharField(max_length=255, blank=True, default="")
    handled = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        url = f"https://codefrog.io/admin/web/message/{self.pk}/change/"
        message = f"""
        A customer send a new feedback message:

        <blockquote>
            {self.message}
        </blockquote>

        Check it out here:
            {url}
        """
        send_mail(
            "[CODEFROG] New feedback from customer!",
            message,
            settings.DEFAULT_FROM_EMAIL,
            [settings.ADMIN_EMAIL],
        )
