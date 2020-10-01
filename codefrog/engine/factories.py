import datetime

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyDateTime

from engine.models import Issue, PullRequest

LABELS = [
    'easy', 'hard', 'important',
    'ux', 'documentation', 'ui',
    'frontend', 'backend', 'good first issue',
    'Browser: IE', 'Browser: Safari',
    'HTML', 'comp:cloud', 'comp:core',
    'wontfix', 'estimation needed',
    'bug', 'regression', 'fix',
    'Type: bug', 'kind/bug', 'debt', 'perf-bloat',
    'crash', 'data-loss',  'uncaught-exception',
    'type:bug/performance',
]


class IssueFactory(DjangoModelFactory):
    issue_refid = factory.Faker('uuid4')
    opened_at = FuzzyDateTime(timezone.now() - datetime.timedelta(days=14), timezone.now() - datetime.timedelta(days=7))
    closed_at = FuzzyDateTime(timezone.now() - datetime.timedelta(days=6), timezone.now() - datetime.timedelta(days=1))

    labels = factory.Faker('words', ext_word_list=LABELS, unique=True)

    class Meta:
        model = Issue


class PullRequestFactory(DjangoModelFactory):
    pull_request_refid = factory.Faker('uuid4')
    opened_at = FuzzyDateTime(timezone.now() - datetime.timedelta(days=14), timezone.now() - datetime.timedelta(days=7))
    merged_at = FuzzyDateTime(timezone.now() - datetime.timedelta(days=6), timezone.now() - datetime.timedelta(days=1))
    age = factory.LazyAttribute(lambda obj: (obj.merged_at - obj.opened_at).days)

    class Meta:
        model = PullRequest

