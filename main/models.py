import json

import jsonfield
import plivo
import twilio.rest
import pytz

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


def choices(*args):
    return zip(args, args)

class SMSNumber(models.Model):
    phone_number = models.CharField(max_length=255)
    service = models.CharField(max_length=10, default='plivo', choices=choices(('plivo', 'twilio')))

    def __str__(self):
        return self.phone_number

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    pseudonym = models.CharField(max_length=255, blank=True, null=True, unique=True, default='Anonymous User')
    phone_number = models.CharField(max_length=255, blank=True)
    phone_info = jsonfield.JSONField(max_length=255, blank=True, null=True)
    send_by_phone = models.BooleanField(default=False)
    send_by_email = models.BooleanField(default=False)
    timezone = models.CharField(max_length=255, choices=choices(*sorted(pytz.all_timezones_set)), default='US/Eastern')
    server_number = models.ForeignKey(SMSNumber, blank=True, null=True, related_name='profiles')

    def send_sms(self, text):
        message = SMSMessage(user=self.user, phone_number=self.phone_number, text=text, server_number=self.server_number)
        message.send()
        return message

    def fetch_phone_info(self):
        twilio_client = twilio.rest.Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        number = twilio_client.lookups.phone_numbers("+%s" % self.phone_number).fetch(type="carrier")
        self.phone_info = number.carrier
        self.save()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.db_manager(instance._state.db).create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


class Hypo(models.Model):
    title = models.CharField(max_length=255)
    text = models.TextField()
    send_time = models.DateTimeField(blank=True, null=True, help_text="Hypo will be sent on or after this time, if status is 'queued'")
    users = models.ManyToManyField(User, through='Vote', related_name='hypos')
    status = models.CharField(max_length=20, choices=choices('draft', 'queued', 'sent'), default='draft')

    class Meta:
        ordering = ['-send_time']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('single_hypo', args=[str(self.id)])

class SMSMessage(models.Model):
    user = models.ForeignKey(User, related_name='sms_messages', blank=True, null=True)
    phone_number = models.CharField(max_length=255)
    server_number = models.ForeignKey(SMSNumber, blank=True, null=True)
    text = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    success = models.NullBooleanField()
    api_response = jsonfield.JSONField(blank=True, null=True)

    def send(self):
        sms_client = plivo.RestAPI(settings.PLIVO_AUTH_ID, settings.PLIVO_AUTH_TOKEN)
        try:
            response = sms_client.send_message({
                'src': self.server_number.phone_number,
                'dst' : self.phone_number,
                'text' : self.text
            })
            self.success = response[0] == 202
            self.api_response = response
        except Exception as e:
            self.success = False
            self.api_response = str(e)
        self.save()

class SMSResponse(models.Model):
    user = models.ForeignKey(User, related_name='sms_responses', blank=True, null=True)
    phone_number = models.CharField(max_length=255)
    server_number = models.ForeignKey(SMSNumber, blank=True, null=True)
    message_uuid = models.CharField(max_length=255, blank=True, null=True)
    text = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    api_response = jsonfield.JSONField(blank=True, null=True)
    verified = models.BooleanField(default=False, help_text='Whether message is verified as coming from Plivo')

    class Meta:
        ordering = ['date']

class VoteQuerySet(models.QuerySet):
    def complete(self):
        return self.exclude(fair_use_vote=None)

class Vote(models.Model):
    hypo = models.ForeignKey(Hypo, related_name='votes')
    user = models.ForeignKey(User, related_name='votes')

    sent_date = models.DateTimeField(auto_now_add=True)
    sent_message = models.OneToOneField(SMSMessage, blank=True, null=True, related_name='vote')

    reply_date = models.DateTimeField(blank=True, null=True)
    reply_message = models.OneToOneField(SMSResponse, blank=True, null=True, related_name='vote')

    fair_use_vote = models.NullBooleanField(blank=True, null=True)
    comments = models.ManyToManyField(SMSResponse, related_name='comment_votes', blank=True)

    objects = VoteQuerySet.as_manager()

    def send(self, record=True):
        message = (
            "Hi, %s! Here's your hypo for today:\n\n"
            "%s\n\n"
            "If you had to guess 'yes' or 'no', would a court find this to be fair use?"
        ) % (self.user.first_name, self.hypo.text,)
        sent_message = self.user.profile.send_sms(message)
        if record:
            self.sent_message = sent_message
            self.save()

