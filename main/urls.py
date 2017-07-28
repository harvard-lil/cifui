from django.conf.urls import url
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    url(r'^receive_sms$', views.receive_sms, name='receive_sms'),
    url(r'^hypo/(?P<hypo_id>\d+)$', views.single_hypo, name='single_hypo'),
    url(r'^$', views.home, name='home'),

    # accounts
    url(r'^accounts/login/$', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    url(r'^accounts/logout/$', auth_views.LogoutView.as_view(template_name='logout.html'), name='logout'),
]