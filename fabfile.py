import os

import django
import re


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
try:
    django.setup()
except Exception as e:
    print("WARNING: Can't configure Django -- tasks depending on Django will fail:\n%s" % e)

from urllib.parse import urljoin
import csv
from random import SystemRandom
import pexpect
import plivo
from django.urls import reverse
from django.contrib.auth.models import User
from django.conf import settings
from django.db import IntegrityError, transaction
from fabric.api import local
from fabric.decorators import task
from main import sms
from main.models import Profile


@task(alias='run')
def run_django():
    local("python manage.py runserver")

@task
def run_live():
    port = '8000'

    print("Running ngrok ...")
    ngrok = pexpect.spawn('ngrok', ['http', port])
    ngrok.expect(r'Forwarding\s+(http://.*?\.ngrok\.io)')

    print("Configuring plivo application ...")
    message_url = urljoin(ngrok.match.group(1).decode('ascii'), reverse('receive_sms'))
    sms_client = plivo.RestAPI(settings.PLIVO_AUTH_ID, settings.PLIVO_AUTH_TOKEN)
    response_code, response_info = sms_client.modify_application({
        'app_id': settings.PLIVO_APPLICATION_ID,
        'message_url': message_url
    })
    if response_code == 202:
        print("Plivo message endpoint changed to %s" % message_url)
    else:
        print("Unable to set Plivo message endpoint: %s" % response_info['message'])
        return

    try:
        local("python manage.py runserver 0.0.0.0:%s" % port)
    finally:
        ngrok.close()

@task
def send_pending_hypo():
    sms.send_pending_hypo()

@task
@transaction.atomic
def import_users(csv_path, database='default'):
    words = open('assets/google-10000-english-usa-no-swears.txt').read().strip().split()
    pseudonyms = open('assets/nicknames.txt').read().strip().split("\n")
    existing_usernames = set(User.objects.using(database).values_list('username', flat=True))
    with open(csv_path) as in_file:
        with open('user_passwords.txt', 'a') as password_out:
            csv_file = csv.DictReader(in_file)
            for entry in csv_file:
                if entry['Confirmed text number']:
                    if not entry['Email']:
                        print("WARNING: User %s has no email address. Skipping." % entry['Confirmed text number'])
                        continue
                    if entry['Email'] in existing_usernames:
                        print("WARNING: User %s already exists, skipping." % entry['Email'])
                        continue
                    print(entry['Email'])
                    password = "-".join(SystemRandom().sample(words, 3))
                    available_pseudonyms = list(set(pseudonyms) - set(Profile.objects.using(database).values_list('pseudonym', flat=True)))
                    user = User.objects.db_manager(database).create_user(username=entry['Email'],
                                                    email=entry['Email'],
                                                    first_name=entry['First'],
                                                    last_name=entry['Last'],
                                                    password=password)
                    password_out.write("%s\t%s\n" % (user.email, password))
                    user.profile.pseudonym = SystemRandom().choice(available_pseudonyms)
                    user.profile.phone_number = '1' + re.sub(r'\D', '', entry['Confirmed text number'])
                    user.profile.send_by_phone = True
                    user.profile.save(using=database)

@task
def send_password_emails(path):
    from django.core.mail import send_mail

    lines = open(path).read().strip().split("\n")
    emails = {}
    for line in lines:
        print(line)
        k, v = line.split("\t")
        emails[k] = v
    for email, password in emails.items():
        send_mail('Your CanIFairUseIt website account', """
Hi!

We'll shortly start sending out the daily hypo for the CanIFairUseIt experiment. Once you've sent your response,
you can view other anonymized responses here:

Website:  https://canifairuseit.com/
Username: %s
Password: %s

Please let us know if you have any questions.

Best,
Jack, Kyle, and Katie
""" % (email, password), 'info@canifairuseit.com', [email])


@task
def fetch_all_phone_info():
    for profile in Profile.objects.exclude(phone_number='').filter(phone_info=None):
        print(profile.phone_number)
        profile.fetch_phone_info()