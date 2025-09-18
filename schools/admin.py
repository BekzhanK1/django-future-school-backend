from django.contrib import admin
from .models import School, Classroom, ClassroomUser


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'country', 'contact_email', 'contact_phone')
    list_filter = ('country', 'city')
    search_fields = ('name', 'city', 'contact_email', 'kundelik_id')
    ordering = ('name',)
    
    fieldsets = (
        (None, {'fields': ('name', 'city', 'country')}),
        ('Contact Information', {'fields': ('contact_email', 'contact_phone')}),
        ('External Integration', {'fields': ('logo_url', 'kundelik_id')}),
    )


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ('grade', 'letter', 'language', 'school', 'kundelik_id')
    list_filter = ('grade', 'language', 'school')
    search_fields = ('grade', 'letter', 'school__name', 'kundelik_id')
    autocomplete_fields = ('school',)
    ordering = ('school', 'grade', 'letter')
    
    fieldsets = (
        (None, {'fields': ('school', 'grade', 'letter', 'language')}),
        ('External Integration', {'fields': ('kundelik_id',)}),
    )


@admin.register(ClassroomUser)
class ClassroomUserAdmin(admin.ModelAdmin):
    list_display = ('classroom', 'user', 'user_role')
    list_filter = ('classroom__school', 'classroom__grade', 'user__role')
    search_fields = ('classroom__school__name', 'user__username', 'user__email')
    autocomplete_fields = ('classroom', 'user')
    
    def user_role(self, obj):
        return obj.user.role
    user_role.short_description = 'User Role'
    user_role.admin_order_field = 'user__role'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'classroom__school',
            'user'
        )
