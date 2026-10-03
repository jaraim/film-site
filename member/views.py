# -*- coding: utf-8 -*-
"""会员与积分视图：注册 / 登录 / 登出 / 用户中心 / 签到 / 充值 / 积分明细。"""
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.shortcuts import render, redirect, get_object_or_404

from .models import Profile, PointRecord, VideoAccess


def register(request):
    """用户注册（注册即送 100 积分）。"""
    if request.user.is_authenticated:
        return redirect("member:center")
    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "注册成功，已赠送 100 积分！")
        return redirect("member:center")
    return render(request, "member/register.html", {"form": form})


def login_view(request):
    """用户登录。"""
    if request.user.is_authenticated:
        return redirect("member:center")
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        messages.success(request, f"欢迎回来，{user.username}")
        return redirect("member:center")
    return render(request, "member/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("videos:home")


@login_required
def center(request):
    """用户中心：积分余额 + 最近流水 + 已解锁影片。"""
    profile = request.user.profile
    records = request.user.point_records.all()[:20]
    accesses = VideoAccess.objects.filter(user=request.user).select_related("video")[:12]
    need_video = None
    need_pk = request.GET.get("need")
    if need_pk:
        from videos.models import Video
        try:
            need_video = Video.objects.get(pk=int(need_pk))
        except (Video.DoesNotExist, ValueError):
            need_video = None
    ctx = {
        "profile": profile,
        "records": records,
        "accesses": accesses,
        "can_checkin": _can_checkin(request.user),
        "need_video": need_video,
    }
    return render(request, "member/center.html", ctx)


@login_required
def checkin(request):
    """每日签到 +5 积分。"""
    user = request.user
    profile = user.profile
    if _can_checkin(user):
        profile.points += 5
        profile.checkin_count += 1
        from django.utils import timezone
        profile.last_checkin = timezone.localdate()
        profile.save(update_fields=["points", "checkin_count", "last_checkin"])
        PointRecord.objects.create(
            user=user, change_type="checkin", delta=5,
            balance=profile.points, note="每日签到",
        )
        messages.success(request, "签到成功，+5 积分！")
    else:
        messages.info(request, "今天已签到过，明天再来吧~")
    return redirect("member:center")


@login_required
def recharge(request):
    """积分充值（演示：可选额度直接到账）。"""
    if request.method == "POST":
        amount = int(request.POST.get("amount", 0) or 0)
        if amount > 0:
            profile = request.user.profile
            profile.points += amount
            profile.save(update_fields=["points"])
            PointRecord.objects.create(
                user=request.user, change_type="recharge", delta=amount,
                balance=profile.points, note=f"充值 {amount} 积分（演示）",
            )
            messages.success(request, f"充值成功，到账 {amount} 积分！")
        else:
            messages.error(request, "充值金额无效")
        return redirect("member:center")
    return render(request, "member/recharge.html")


@login_required
def point_records(request):
    """全部积分流水。"""
    records = request.user.point_records.all()[:100]
    return render(request, "member/records.html", {"records": records})


def _can_checkin(user):
    """今天是否可签到。"""
    from django.utils import timezone
    return user.profile.last_checkin != timezone.localdate()
