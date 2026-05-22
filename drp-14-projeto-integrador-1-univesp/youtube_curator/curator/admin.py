from django.contrib import admin
from .models import TrainingModule, CuratedVideo, UserProgress


@admin.register(TrainingModule)
class TrainingModuleAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_by", "video_count")
    list_filter = ("created_by",)
    prepopulated_fields = {"slug": ("name",)}

    def video_count(self, obj):
        return obj.videos.count()
    video_count.short_description = "Vídeos"


@admin.register(CuratedVideo)
class CuratedVideoAdmin(admin.ModelAdmin):
    list_display = ("title", "module", "channel_name", "duration", "added_by", "created_at")
    list_filter = ("module",)
    search_fields = ("title", "channel_name")
    readonly_fields = ("created_at",)


@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "video", "watched", "watched_at")
    list_filter = ("watched",)
