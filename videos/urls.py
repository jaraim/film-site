# -*- coding: utf-8 -*-
from django.urls import path
from . import views

app_name = "videos"

urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search, name="search"),
    path("category/<slug:slug>/", views.category, name="category"),
    path("video/<int:pk>/", views.detail, name="detail"),
    path("play/<int:pk>/", views.play, name="play"),
]
