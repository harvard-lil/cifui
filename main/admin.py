from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import Hypo, Profile, Vote, SMSMessage, SMSResponse


### Helpers ###

def new_class(name, *args, **kwargs):
    return type(name, args, kwargs)

# change Django defaults, because 'extra' isn't helpful anymore now you can add more with javascript
admin.TabularInline.extra = 0
admin.StackedInline.extra = 0


### User ###
# via https://simpleisbetterthancomplex.com/tutorial/2016/11/23/how-to-add-user-profile-to-django-admin.html

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'

class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline, )
    list_display = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'send_by_phone', 'is_staff')
    list_editable = ('first_name', 'last_name',)

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(CustomUserAdmin, self).get_inline_instances(request, obj)

    def phone_number(self, obj):
        return obj.profile.phone_number

    def send_by_phone(self, obj):
        return obj.profile.send_by_phone

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


### Hypo ###

class VoteInline(admin.TabularInline):
    model = Vote
    show_change_link = True
    raw_id_fields = ['comments']

class HypoAdmin(admin.ModelAdmin):
    inlines = [VoteInline]
    list_display = ('title', 'status', 'send_time')
admin.site.register(Hypo, HypoAdmin)


### SMS ###

class SMSMessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'text', 'success', 'date')
admin.site.register(SMSMessage, SMSMessageAdmin)

class SMSResponseAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'text', 'date')
admin.site.register(SMSResponse, SMSResponseAdmin)


### Vote ###

class CommentInline(admin.TabularInline):
    model = Vote.comments.through
    show_change_link = True
    fields = ['date', 'text']
    readonly_fields = ['date', 'text']

    def date(self, obj):
        return obj.smsresponse.date

    def text(self, obj):
        return obj.smsresponse.text

class VoteAdmin(admin.ModelAdmin):
    inlines = [CommentInline]
    list_display = ('hypo', 'user', 'sent_date', 'reply_date', 'fair_use_vote')
admin.site.register(Vote, VoteAdmin)