# -*- coding: utf-8 -*-
"""会员与积分系统：Profile（积分余额）/ PointRecord（积分流水）/ VideoAccess（已解锁付费片）。"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class Profile(models.Model):
    """用户积分档案（一对一扩展 Django User）。"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, verbose_name="用户",
        on_delete=models.CASCADE, related_name="profile",
    )
    points = models.IntegerField("积分余额", default=0)
    # 累计签到次数
    checkin_count = models.IntegerField("累计签到", default=0)
    last_checkin = models.DateField("最近签到日", null=True, blank=True)
    created_at = models.DateTimeField("注册时间", auto_now_add=True)

    class Meta:
        verbose_name = "用户积分"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.user.username} · {self.points}积分"


class PointRecord(models.Model):
    """积分变动流水。"""
    TYPE_CHOICES = [
        ("register", "注册奖励"),
        ("checkin", "每日签到"),
        ("recharge", "积分充值"),
        ("consume", "观看扣费"),
        ("admin", "管理员调整"),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="用户",
        on_delete=models.CASCADE, related_name="point_records",
    )
    change_type = models.CharField("类型", max_length=20, choices=TYPE_CHOICES)
    delta = models.IntegerField("变动积分", default=0)  # 正=增加，负=扣减
    balance = models.IntegerField("变动后余额", default=0)
    note = models.CharField("备注", max_length=200, blank=True, default="")
    created_at = models.DateTimeField("时间", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "积分流水"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.user.username} {self.get_change_type_display()} {self.delta:+d}"


class VideoAccess(models.Model):
    """用户已解锁的付费影视（重复观看不再扣积分）。"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="用户",
        on_delete=models.CASCADE, related_name="video_access",
    )
    video = models.ForeignKey(
        "videos.Video", verbose_name="影视",
        on_delete=models.CASCADE, related_name="access_users",
    )
    created_at = models.DateTimeField("解锁时间", default=timezone.now)

    class Meta:
        unique_together = [("user", "video")]
        ordering = ["-created_at"]
        verbose_name = "解锁记录"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.user.username} → {self.video.title}"
