import json

import plivo

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from .models import Hypo, Vote


sms_client = plivo.RestAPI(settings.PLIVO_AUTH_ID, settings.PLIVO_AUTH_TOKEN)

def send_pending_hypo():
    # find and claim next hypo
    with transaction.atomic():
        hypo = Hypo.objects.filter(status='queued', send_time__lte=timezone.now()).select_for_update().first()
        if not hypo:
            # nothing to send
            return
        hypo.status = 'sent'
        hypo.save()

    # send hypo to each user
    users = User.objects.select_related('profile').filter(profile__send_by_phone=True)
    for user in users:

        # double check we're not resending
        if user.votes.filter(hypo=hypo).exists():
            continue

        # record send
        vote = Vote(hypo=hypo, user=user)
        vote.save()

        # send
        message = (
            "Hello! Here's your hypo for today:\n\n"
            "%s\n\n"
            "If you had to guess 'yes' or 'no', would a court find this to be fair use?"
        ) % (hypo.text,)
        vote.sent_message = user.profile.send_sms(message)
        vote.save()
