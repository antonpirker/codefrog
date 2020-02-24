from django.conf import settings as django_settings

def settings(request):
    return {
        'LIVE_SYSTEM': django_settings.LIVE_SYSTEM,
    }
