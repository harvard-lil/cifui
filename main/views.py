import re
from django.contrib.auth.models import User
from django.contrib.humanize.templatetags.humanize import ordinal
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .sms import sms_client
from .models import Hypo, SMSResponse, Vote


def home(request):
    hypos = Hypo.objects.filter(status='sent')
    return render(request, 'home.html', {'hypos': hypos})

def single_hypo(request, hypo_id):
    hypo = get_object_or_404(Hypo, pk=hypo_id)
    return render(request, 'hypo.html', {'hypo': hypo})

@csrf_exempt
def receive_sms(request):
    print("SMS RECEIVED:", request.POST)
    from_number = request.POST.get('From')
    text = request.POST.get('Text')

    user = User.objects.filter(profile__phone_number=from_number).first()

    # record all messages
    sms_response = SMSResponse(user=user, text=text, phone_number=from_number)
    sms_response.save()

    # verify origin
    response = sms_client.get_message({'message_uuid': request.POST.get('MessageUUID')})
    if response[0] != 200:
        return HttpResponse()  # return blank response for unverified message
    sms_response.verified = True
    sms_response.save()

    # process
    if user:
        vote = Vote.objects.filter(user=user).order_by('-sent_date').first()
        hypo_url = request.build_absolute_uri(vote.hypo.get_absolute_url())

        # only let them vote once
        if vote.reply_date:
            user.profile.send_sms("You have already responded to the latest hypo. See all responses at %s" % hypo_url)
            return HttpResponse()

        # parse vote
        fair_use_vote = None
        if re.search(r'\byes\b', text, flags=re.I):
            fair_use_vote = True
        elif re.search(r'\bno\b', text, flags=re.I):
            fair_use_vote = False

        if fair_use_vote is None:
            # can't parse response
            user.profile.send_sms("We don't understand your response. Please respond 'yes' or 'no'.")

        else:
            # record vote
            vote.fair_use_vote = fair_use_vote
            vote.reply_message = sms_response
            vote.reply_date = timezone.now()
            vote.save()

            # send confirmation
            vote_count = vote.hypo.votes.exclude(reply_date__isnull=True).count()
            message = (
                "Your prediction has been recorded as: %s. "
                "You are the %s person to respond. "
                "You can see other responses at %s."
            ) % (
                "yes, a court would find fair use" if fair_use_vote else "no, a court would not find fair use",
                ordinal(vote_count),
                hypo_url
            )
            user.profile.send_sms(message)

    return HttpResponse()