# -*- coding: utf-8 -*-
"""初始化站点分类结构（两级）。

用法：
  python manage.py setup_categories

建立的分类树：
  电影    → 动作片/喜剧片/爱情片/科幻片/恐怖片/剧情片/战争片/伦理片
  电视剧  → 国产剧/海外剧
  动漫    → 国产动漫/海外动漫/里番动漫
  短剧    → (一级，无二级)

注意：默认会删除已有分类并重建；--keep 可保留。
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from videos.models import Category, Video, VideoSource

# 分类树定义：(一级名, 一级slug, [二级(名, slug)])
TREE = [
    ("电影", "movie", [
        ("动作片", "action"), ("喜剧片", "comedy"), ("爱情片", "romance"),
        ("科幻片", "scifi"), ("恐怖片", "horror"), ("剧情片", "drama"),
        ("战争片", "war"), ("伦理片", "ethic"),
    ]),
    ("电视剧", "tv", [("国产剧", "domestic"), ("海外剧", "overseas")]),
    ("动漫", "anime", [
        ("国产动漫", "domestic"), ("海外动漫", "overseas"), ("里番动漫", "rfan"),
    ]),
    ("短剧", "short", []),
]


class Command(BaseCommand):
    help = "初始化站点两级分类结构"

    def add_arguments(self, parser):
        parser.add_argument("--keep", action="store_true", help="保留已有分类（仅补缺）")

    @transaction.atomic
    def handle(self, *args, **opts):
        keep = opts["keep"]
        if not keep:
            # 清空旧分类（关联影视置空）
            Video.objects.update(category=None)
            Category.objects.all().delete()
            self.stdout.write("已清空旧分类")

        order = 0
        for root_name, root_slug, children in TREE:
            root, _ = Category.objects.get_or_create(
                name=root_name, parent=None,
                defaults={"sort": order, "slug": root_slug},
            )
            order += 1
            if children:
                for i, (child, child_slug) in enumerate(children):
                    Category.objects.get_or_create(
                        name=child, parent=root,
                        defaults={"sort": i, "slug": child_slug},
                    )
            self.stdout.write(f"  ✓ {root_name}"
                              + (f" → {', '.join(c[0] for c in children)}" if children else ""))

        total = Category.objects.count()
        self.stdout.write(self.style.SUCCESS(f"分类初始化完成，共 {total} 个分类"))
