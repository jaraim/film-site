"""URL configuration for film-site."""
from django.contrib import admin
from django.urls import include, path

from collector.views import collect_view

urlpatterns = [
    # 后台采集页面（必须先于 admin.site.urls，否则被其拦截404）
    path("admin/collect/", admin.site.admin_view(collect_view), name="admin_collect"),
    path("admin/", admin.site.urls),
    path("", include("videos.urls")),
    path("member/", include("member.urls")),
]
