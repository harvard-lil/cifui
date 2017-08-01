from .settings_base import *

ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': env.db()
}

EMAIL_HOST = 'smtp.mailgun.org'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'postmaster@canifairuseit.com'
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
EMAIL_USE_TLS = True

ADMINS = env.json('ADMINS')