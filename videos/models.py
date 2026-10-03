# -*- coding: utf-8 -*-
"""影视站数据模型：分类 / 影视 / 播放源。"""
from django.db import models
from django.urls import reverse


class Category(models.Model):
    """影视分类（类型），对应苹果CMS的 type_name。支持两级：一级大类 → 二级子类。"""
    name = models.CharField("分类名称", max_length=50)
    parent = models.ForeignKey(
        "self", verbose_name="上级分类", on_delete=models.CASCADE,
        null=True, blank=True, related_name="children",
    )
    slug = models.SlugField("URL别名", max_length=60, blank=True)
    sort = models.IntegerField("排序", default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort", "id"]
        verbose_name = "分类"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.parent.name} › {self.name}" if self.parent else self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            base = slugify(self.name) or "cat"
            self.slug = base
            n = 2
            while Category.objects.exclude(pk=self.pk).filter(slug=self.slug).exists():
                self.slug = f"{base}-{n}"
                n += 1
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("videos:category", args=[self.slug])

    @property
    def is_root(self):
        return self.parent is None


class Video(models.Model):
    """影视条目（采集入库）。"""
    TYPE_CHOICES = [
        ("movie", "电影"),
        ("tv", "电视剧"),
        ("variety", "综艺"),
        ("anime", "动漫"),
        ("doc", "纪录片"),
    ]

    title = models.CharField("片名", max_length=200, db_index=True)
    original_title = models.CharField("原名", max_length=200, blank=True, default="")
    category = models.ForeignKey(
        Category, verbose_name="分类", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="videos",
    )
    video_type = models.CharField("影视类型", max_length=20, choices=TYPE_CHOICES, default="movie")
    year = models.CharField("年份", max_length=10, blank=True, default="")
    area = models.CharField("地区", max_length=50, blank=True, default="")
    director = models.CharField("导演", max_length=200, blank=True, default="")
    actors = models.TextField("主演", blank=True, default="")
    description = models.TextField("简介", blank=True, default="")
    poster = models.URLField("海报", max_length=500, blank=True, default="")
    remark = models.CharField("更新备注", max_length=100, blank=True, default="")

    # 播放设置（可被播放器读取）
    skip_intro = models.FloatField("片头跳过秒数", default=0)
    skip_outro = models.FloatField("片尾跳过秒数", default=0)
    # 付费观看所需积分（0 = 免费）
    need_points = models.IntegerField("观看所需积分", default=0)

    status = models.CharField(
        "状态", max_length=20,
        choices=[("ongoing", "连载中"), ("ended", "已完结")],
        default="ongoing",
    )
    is_active = models.BooleanField("上架", default=True)
    views = models.PositiveIntegerField("点击量", default=0)
    created_at = models.DateTimeField("入库时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [models.Index(fields=["title"])]
        verbose_name = "影视"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("videos:detail", args=[self.pk])

    def source_list(self):
        """该片所有播放源（按排序）。"""
        return self.sources.all()


class VideoSource(models.Model):
    """一个影视的一个播放源（如 非凡M3U8 / 非凡线路），内含若干剧集。"""
    video = models.ForeignKey(
        Video, verbose_name="影视", on_delete=models.CASCADE, related_name="sources"
    )
    # 播放源标识，如 ffm3u8 / feifan（对应苹果CMS的 from）
    from_flag = models.CharField("播放源标识", max_length=50)
    name = models.CharField("线路名称", max_length=100)
    sort = models.IntegerField("排序", default=0)
    # 剧集列表：每项 {"name":"第1集","url":"..."}
    episodes = models.JSONField("剧集", default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort", "id"]
        unique_together = [("video", "from_flag")]
        verbose_name = "播放源"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.video.title} / {self.name}"

    def episode_list(self):
        """返回 [(序号, 剧名, 地址)]。"""
        return [(i + 1, ep.get("name", f"第{i+1}集"), ep.get("url", ""))
                for i, ep in enumerate(self.episodes)]
