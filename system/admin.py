# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import SiteConfig, AdSlot, Ad, PlayerConfig


@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    list_display = ["key", "value", "description", "updated_at"]
    search_fields = ["key", "description"]
    list_editable = ["value"]


class AdInline(admin.TabularInline):
    model = Ad
    extra = 1
    fields = ["title", "ad_type", "code", "image", "link", "sort", "is_active"]


@admin.register(AdSlot)
class AdSlotAdmin(admin.ModelAdmin):
    list_display = ["name", "position", "width", "height", "is_active"]
    list_editable = ["is_active"]
    inlines = [AdInline]


@admin.register(Ad)
class AdAdmin(admin.ModelAdmin):
    list_display = ["title", "slot", "ad_type", "sort", "is_active"]
    list_filter = ["ad_type", "slot", "is_active"]
    search_fields = ["title"]
    list_editable = ["sort", "is_active"]


@admin.register(PlayerConfig)
class PlayerConfigAdmin(admin.ModelAdmin):
    list_display = ["key", "value", "description", "updated_at"]
    search_fields = ["key", "description"]
    list_editable = ["value"]
