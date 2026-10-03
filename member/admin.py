# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import Profile, PointRecord, VideoAccess


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "points", "checkin_count", "last_checkin", "created_at"]
    search_fields = ["user__username"]
    list_filter = ["last_checkin"]


@admin.register(PointRecord)
class PointRecordAdmin(admin.ModelAdmin):
    list_display = ["user", "change_type", "delta", "balance", "note", "created_at"]
    list_filter = ["change_type"]
    search_fields = ["user__username", "note"]


@admin.register(VideoAccess)
class VideoAccessAdmin(admin.ModelAdmin):
    list_display = ["user", "video", "created_at"]
    search_fields = ["user__username", "video__title"]
