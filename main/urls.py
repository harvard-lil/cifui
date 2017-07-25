from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^receive_sms$', views.receive_sms, name='receive_sms'),
    url(r'^hypo/(?P<hypo_id>\d+)$', views.single_hypo, name='single_hypo'),
    url(r'^$', views.home, name='home'),
]