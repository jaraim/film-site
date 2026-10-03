# -*- coding: utf-8 -*-
"""初始化系统配置与广告位（可重复执行，仅补缺）。

用法：python manage.py setup_system
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from system.models import AdSlot, SiteConfig, PlayerConfig


class Command(BaseCommand):
    help = "初始化系统配置与广告位"

    @transaction.atomic
    def handle(self, *args, **opts):
        # 广告位（全部位置）
        slots = [
            ("首页顶部横幅", "home_top", 1200, 100),
            ("首页侧边栏", "home_side", 300, 250),
            ("分类列表顶部", "list_top", 1200, 100),
            ("详情页顶部", "detail_top", 1200, 100),
            ("详情页底部", "detail_bottom", 1200, 100),
            ("播放页顶部", "play_top", 1200, 100),
            ("播放页底部", "play_bottom", 1200, 100),
            ("搜索页顶部", "search_top", 1200, 100),
        ]
        for name, pos, w, h in slots:
            AdSlot.objects.get_or_create(
                position=pos,
                defaults={"name": name, "width": w, "height": h},
            )
        self.stdout.write(f"广告位：{AdSlot.objects.count()} 个")

        # 站点配置
        site_configs = [
            ("site_name", "极简影视", "站点名称"),
            ("site_keywords", "影视,电影,电视剧,动漫,短剧", "站点关键词"),
            ("site_description", "极简影视 - 在线影视观看平台", "站点描述"),
            ("site_logo", "", "站点Logo地址(URL)"),
            ("site_footer", "© 2026 极简影视 · 仅供学习演示", "底部版权信息"),
        ]
        for k, v, desc in site_configs:
            SiteConfig.objects.get_or_create(key=k, defaults={"value": v, "description": desc})
        self.stdout.write(f"站点配置：{SiteConfig.objects.count()} 条")

        # 播放器配置
        player_configs = [
            ("default_rate", "1.0", "默认播放倍速"),
            ("default_skip_intro", "0", "默认片头跳过秒数(全站)"),
            ("default_skip_outro", "0", "默认片尾跳过秒数(全站)"),
            ("auto_next", "1", "是否自动连播(1开/0关)"),
        ]
        for k, v, desc in player_configs:
            PlayerConfig.objects.get_or_create(key=k, defaults={"value": v, "description": desc})
        self.stdout.write(self.style.SUCCESS(f"播放器配置：{PlayerConfig.objects.count()} 条"))
