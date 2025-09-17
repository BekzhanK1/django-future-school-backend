from django.contrib import admin
from .models import User, AuthSession

admin.site.register(User)
admin.site.register(AuthSession)