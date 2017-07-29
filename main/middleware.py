import pytz

from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

# via https://docs.djangoproject.com/en/1.11/topics/i18n/timezones/#selecting-the-current-time-zone
class TimezoneMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.user.is_authenticated:
            try:
                timezone.activate(pytz.timezone(request.user.profile.timezone or 'US/Eastern'))
            except pytz.UnknownTimeZoneError:
                timezone.deactivate()