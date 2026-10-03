# -*- coding: utf-8 -*-
"""系统配置与广告模块：站点配置 / 广告位 / 广告 / 播放器配置。"""
from django.db import models


class SiteConfig(models.Model):
    """站点全局配置（键值对，对标 MacCMS10 系统设置）。"""
    key = models.CharField("配置键", max_length=50, unique=True)
    value = models.CharField("配置值", max_length=500, blank=True, default="")
    description = models.CharField("说明", max_length=200, blank=True, default="")
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        ordering = ["key"]
        verbose_name = "站点配置"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.key} = {self.value}"


class AdSlot(models.Model):
    """广告位。"""
    POSITION_CHOICES = [
        ("home_top", "首页顶部横幅"),
        ("home_side", "首页侧边栏"),
        ("list_top", "分类列表顶部"),
        ("detail_top", "详情页顶部"),
        ("detail_bottom", "详情页底部"),
        ("play_top", "播放页顶部"),
        ("play_bottom", "播放页底部"),
        ("search_top", "搜索页顶部"),
    ]
    name = models.CharField("广告位名称", max_length=50)
    position = models.CharField("位置", max_length=30, choices=POSITION_CHOICES, unique=True)
    # 尺寸提示（供后台参考）
    width = models.IntegerField("宽度(px)", default=0)
    height = models.IntegerField("高度(px)", default=0)
    is_active = models.BooleanField("启用", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "广告位"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    def active_ads(self):
        return self.ads.filter(is_active=True).order_by("sort")


class Ad(models.Model):
    """广告内容。支持代码广告 / 图片链接广告。"""
    TYPE_CHOICES = [
        ("code", "代码广告"),
        ("image", "图片广告"),
    ]
    slot = models.ForeignKey(
        AdSlot, verbose_name="所属广告位",
        on_delete=models.CASCADE, related_name="ads",
    )
    title = models.CharField("广告标题", max_length=100)
    ad_type = models.CharField("类型", max_length=10, choices=TYPE_CHOICES, default="code")
    # 代码广告：直接渲染 HTML/JS
    code = models.TextField("代码内容", blank=True, default="")
    # 图片广告
    image = models.URLField("图片地址", max_length=500, blank=True, default="")
    link = models.URLField("跳转链接", max_length=500, blank=True, default="")
    alt = models.CharField("图片描述", max_length=100, blank=True, default="")
    sort = models.IntegerField("排序", default=0)
    is_active = models.BooleanField("启用", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        ordering = ["sort", "id"]
        verbose_name = "广告"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.title} [{self.slot.name}]"

    def render(self):
        """渲染广告 HTML。"""
        if self.ad_type == "code" and self.code:
            return self.code
        if self.ad_type == "image" and self.image:
            tag = f'<a href="{self.link or "#"}" target="_blank" rel="noopener"><img src="{self.image}" alt="{self.alt or self.title}" style="max-width:100%;"></a>'
            return tag
        return ""


class PlayerConfig(models.Model):
    """播放器全局配置（默认值，用户可覆盖）。"""
    key = models.CharField("配置键", max_length=50, unique=True)
    value = models.CharField("配置值", max_length=200, blank=True, default="")
    description = models.CharField("说明", max_length=200, blank=True, default="")
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        ordering = ["key"]
        verbose_name = "播放器配置"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.key} = {self.value}"
