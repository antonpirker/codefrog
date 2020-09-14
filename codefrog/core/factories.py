import datetime
import random

import factory
from django.conf import settings
from django.utils import timezone
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyDateTime

from core.models import Project, Release
from engine.factories import IssueFactory, PullRequestFactory


class UserFactory(DjangoModelFactory):
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    username = factory.LazyAttribute(lambda obj: '%s%s' % (obj.first_name.lower(), obj.last_name.lower()))
    email = factory.LazyAttribute(lambda obj: '%s@example.com' % obj.username)

    class Meta:
        model = settings.AUTH_USER_MODEL


class ReleaseFactory(DjangoModelFactory):
    class Meta:
        model = Release

    name = factory.Sequence(lambda n: 'v%d.0' % n)
    timestamp = FuzzyDateTime(timezone.now() - datetime.timedelta(days=30), timezone.now())


class ProjectFactory(DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    name = factory.Faker('catch_phrase')
    slug = factory.Faker('slug')

    class Meta:
        model = Project

    release_set = factory.RelatedFactoryList(
        ReleaseFactory, factory_related_name='project',
        size=lambda: random.randint(3, 10),
    )

    issue_set = factory.RelatedFactoryList(
        IssueFactory, factory_related_name='project',
        size=lambda: random.randint(15, 50),
    )

    pullrequest_set = factory.RelatedFactoryList(
        PullRequestFactory, factory_related_name='project',
        size=lambda: random.randint(5, 10),
    )
