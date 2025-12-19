from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, AuthSession, PasswordResetToken


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name',
                    'last_name', 'role', 'school', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser', 'school')
    search_fields = ('username', 'email', 'first_name',
                     'last_name', 'kundelik_id')
    ordering = ('username',)
    # For managing parent-child relationships
    filter_horizontal = ('children',)

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name',
         'last_name', 'email', 'phone_number')}),
        ('School info', {'fields': ('school', 'kundelik_id')}),
        ('Role', {'fields': ('role',)}),
        ('Parent-Child Relationships', {
            'fields': ('children',),
            'description': 'For parent accounts: select student children. For student accounts: shows linked parents (read-only).',
            'classes': ('collapse',),
        }),
        ('Permissions', {'fields': ('is_active', 'is_staff',
         'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'school'),
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        """Make children field read-only for students (they see parents instead)"""
        readonly = list(super().get_readonly_fields(request, obj))
        if obj and obj.role == 'student':
            readonly.append('children')
        return readonly


@admin.register(AuthSession)
class AuthSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'is_active', 'created_at',
                    'expires_at', 'ip_address')
    list_filter = ('is_active', 'created_at', 'expires_at')
    search_fields = ('user__username', 'user__email', 'ip_address')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'used', 'created_at', 'expires_at')
    list_filter = ('used', 'created_at', 'expires_at')
    search_fields = ('user__username', 'user__email', 'token')
    readonly_fields = ('created_at', 'token')
    ordering = ('-created_at',)
