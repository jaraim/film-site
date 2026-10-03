# -*- coding: utf-8 -*-
from django.urls import path
from . import views

app_name = "member"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("center/", views.center, name="center"),
    path("checkin/", views.checkin, name="checkin"),
    path("recharge/", views.recharge, name="recharge"),
    path("records/", views.point_records, name="records"),
]
