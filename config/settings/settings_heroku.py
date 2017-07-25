from .settings_base import *

ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': env.db()
}