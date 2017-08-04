# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-08-04 01:54
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0007_profile_phone_info'),
    ]

    operations = [
        migrations.CreateModel(
            name='SMSNumber',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone_number', models.CharField(max_length=255)),
                ('service', models.CharField(choices=[(('plivo', 'twilio'), ('plivo', 'twilio'))], default='plivo', max_length=10)),
            ],
        ),
        migrations.AddField(
            model_name='smsresponse',
            name='api_response',
            field=jsonfield.fields.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='smsresponse',
            name='message_uuid',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='smsmessage',
            name='api_response',
            field=jsonfield.fields.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='server_number',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='profiles', to='main.SMSNumber'),
        ),
        migrations.AddField(
            model_name='smsmessage',
            name='server_number',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='main.SMSNumber'),
        ),
        migrations.AddField(
            model_name='smsresponse',
            name='server_number',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='main.SMSNumber'),
        ),
    ]
