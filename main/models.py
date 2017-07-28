import json

import plivo
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

def choices(*args):
    return zip(args, args)

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    pseudonym = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=255, blank=True)
    send_by_phone = models.BooleanField(default=False)
    send_by_email = models.BooleanField(default=False)

    def send_sms(self, text):
        message = SMSMessage(user=self.user, phone_number=self.phone_number, text=text)
        message.send()
        return message

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

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
        ordering = ['send_time']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('single_hypo', args=[str(self.id)])

class SMSMessage(models.Model):
    user = models.ForeignKey(User, related_name='sms_messages', blank=True, null=True)
    phone_number = models.CharField(max_length=255)
    text = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    success = models.NullBooleanField()
    api_response = models.TextField(blank=True, null=True)

    def send(self):
        sms_client = plivo.RestAPI(settings.PLIVO_AUTH_ID, settings.PLIVO_AUTH_TOKEN)
        try:
            response = sms_client.send_message({
                'src': settings.PLIVO_FROM_NUMBER,
                'dst' : self.phone_number,
                'text' : self.text
            })
            self.success = response[0] == 202
            self.api_response = json.dumps(response)
        except Exception as e:
            self.success = False
            self.api_response = str(e)
        self.save()

class SMSResponse(models.Model):
    user = models.ForeignKey(User, related_name='sms_responses', blank=True, null=True)
    phone_number = models.CharField(max_length=255)
    text = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False, help_text='Whether message is verified as coming from Plivo')

    class Meta:
        ordering = ['date']

class Vote(models.Model):
    hypo = models.ForeignKey(Hypo, related_name='votes')
    user = models.ForeignKey(User, related_name='votes')

    sent_date = models.DateTimeField(auto_now_add=True)
    sent_message = models.OneToOneField(SMSMessage, blank=True, null=True, related_name='vote')

    reply_date = models.DateTimeField(blank=True, null=True)
    reply_message = models.OneToOneField(SMSResponse, blank=True, null=True, related_name='vote')

    fair_use_vote = models.NullBooleanField(blank=True, null=True)
    comments = models.ManyToManyField(SMSResponse, related_name='comment_votes')