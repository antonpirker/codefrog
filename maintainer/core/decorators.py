from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.http import Http404

from core.models import Project


def only_matching_authenticated_users(func):
    """
    Check if the user is authenticated and matching with the username in the URL
    """
    def wrapper(*args, **kwargs):
        request = args[0]
        user = request.user

        if not user.is_superuser:
            is_correct_user = user.is_authenticated \
                              and user.username == kwargs['username']

            if not is_correct_user:
                raise PermissionDenied()

        return func(*args, **kwargs)

    return wrapper


def add_user_and_project(func):
    """
    Add the project to the view.
    """
    def wrapper(*args, **kwargs):
        try:
            project = Project.objects.get(slug=kwargs['project_slug'])
        except Project.DoesNotExist:
            raise Http404('Project does not exist')

        try:
            user = User.objects.get(username=kwargs['username'])
        except User.DoesNotExist:
            raise Http404('User does not exist')

        if not user.projects.filter(pk=project.pk).exists():
            raise Http404('Project does not belong to user')

        kwargs['user'] = user
        kwargs['project'] = project

        return func(*args, **kwargs)

    return wrapper