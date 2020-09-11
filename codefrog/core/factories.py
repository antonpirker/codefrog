import factory
from django.conf import settings
from factory.django import DjangoModelFactory

from core.models import Project


class UserFactory(DjangoModelFactory):
    class Meta:
        model = settings.AUTH_USER_MODEL

    username = factory.Sequence(lambda n: 'user%d' % n)
    email = factory.LazyAttribute(lambda obj: '%s@example.com' % obj.username)

    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')


class ProjectFactory(DjangoModelFactory):
    class Meta:
        model = Project

    user = factory.SubFactory(UserFactory)
    name = factory.Faker('catch_phrase')
    slug = factory.Faker('slug')
