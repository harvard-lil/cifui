import re

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.humanize.templatetags.humanize import ordinal
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .sms import sms_client
from .models import Hypo, SMSResponse, Vote


@login_required
def home(request):
    hypos = list(Hypo.objects.filter(status='sent'))
    voted_in_latest = hypos[0].votes.complete().filter(user=request.user).exists()
    return render(request, 'home.html', {
        'hypos': hypos,
        'voted_in_latest': voted_in_latest
    })

@login_required
def single_hypo(request, hypo_id):
    hypo = get_object_or_404(Hypo, pk=hypo_id, status='sent')
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

        # only let them vote once
        if vote.reply_date:
            vote.comments.add(sms_response)
            return HttpResponse()

        # parse vote
        m = re.match(r'^[\s\.\']*(yes|no)[\s\.\']*$', text, flags=re.I)
        if not m:
            # can't parse response
            user.profile.send_sms("We don't understand your response. Please respond 'yes' or 'no'.")
            return HttpResponse()

        # record vote
        fair_use_vote = m.group(1).lower() == 'yes'
        vote.fair_use_vote = fair_use_vote
        vote.reply_message = sms_response
        vote.reply_date = timezone.now()
        vote.save()

        # send confirmation
        vote_count = vote.hypo.votes.exclude(reply_date__isnull=True).count()
        message = (
            "Thanks! Your prediction is: %s.\n"
            "You are the %s person to respond.\n"
            "You can now see other responses at the website.\n"
            "If you have any comments for us about this hypo, you can text them now."
        ) % (
            "yes, a court would find fair use" if fair_use_vote else "no, a court would not find fair use",
            ordinal(vote_count)
        )
        user.profile.send_sms(message)

    return HttpResponse()

