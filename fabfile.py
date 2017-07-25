import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
try:
    django.setup()
except Exception as e:
    print("WARNING: Can't configure Django -- tasks depending on Django will fail:\n%s" % e)

from urllib.parse import urljoin
import pexpect
import plivo
from django.urls import reverse
from django.conf import settings
from fabric.api import local
from fabric.decorators import task
from main import sms


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