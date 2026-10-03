# -*- coding: utf-8 -*-
from django.contrib import admin
from .models import Category, Video, VideoSource


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "sort"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name"]


class VideoSourceInline(admin.TabularInline):
    model = VideoSource
    extra = 0
    fields = ["from_flag", "name", "sort"]


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "video_type", "year", "status", "need_points", "views", "updated_at"]
    list_filter = ["video_type", "status", "category"]
    search_fields = ["title", "director", "actors"]
    inlines = [VideoSourceInline]
    list_editable = ["status", "need_points"]


@admin.register(VideoSource)
class VideoSourceAdmin(admin.ModelAdmin):
    list_display = ["video", "from_flag", "name", "sort"]
    list_filter = ["from_flag"]
    search_fields = ["video__title"]
