
from django.http import HttpResponseRedirect
from django.utils import timezone

from web.models import Message


def feedback(request):
    url = request.META.get('HTTP_REFERER', None)

    if request.method == 'POST':
        message = request.POST.get('message', None)
        if message:
            Message.objects.create(
                timestamp=timezone.now(),
                message=message,
                user=request.user if request.user.is_authenticated else None,
                url=url,
            )

    return HttpResponseRedirect(url)
