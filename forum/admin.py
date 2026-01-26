from django.contrib import admin
from .models import ForumThread, ForumPost, PostReaction


@admin.register(ForumThread)
class ForumThreadAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'subject_group',
                    'created_by', 'created_at', 'updated_at')
    list_filter = ('subject_group', 'created_by', 'created_at', 'updated_at')
    search_fields = ('title', 'subject_group__name', 'created_by__username')
    autocomplete_fields = ('subject_group', 'created_by')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ForumPost)
class ForumPostAdmin(admin.ModelAdmin):
    list_display = ('id', 'thread', 'author', 'content',
                    'created_at', 'updated_at')
    list_filter = ('thread', 'author', 'created_at', 'updated_at')
    search_fields = ('thread__title', 'author__username', 'content')
    autocomplete_fields = ('thread', 'author')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')


@admin.register(PostReaction)
class PostReactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'user', 'reaction_type', 'created_at')
    list_filter = ('post', 'user', 'reaction_type', 'created_at')
