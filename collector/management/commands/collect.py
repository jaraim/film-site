# -*- coding: utf-8 -*-
"""苹果CMS provide/vod 标准采集命令。

用法:
  python manage.py collect --api "http://api.ffzyapi.com/api.php/provide/vod/at/json/"
  python manage.py collect --api "http://.../at/xml/" --pages 5
  python manage.py collect --api "..." --from ffm3u8

支持 json / xml 两种返回格式；按 from 分组生成多条播放源；
多集用标准分隔符解析：集名与地址 "集名$地址" 组合间用 "$$$" 分隔。
"""
import json
import time
import os
import logging
import xml.etree.ElementTree as ET

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from videos.models import Category, Video, VideoSource

# 剥离代理环境变量（部分环境代理无法访问采集接口）
for _k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    os.environ.pop(_k, None)

logger = logging.getLogger(__name__)


def parse_play_data(play_from, play_url):
    """解析苹果CMS play_url。返回 [{name,url}, ...]。

    兼容多种分隔：多集间用 # 或 $$$ 分隔；集内 名$地址。
    播放源名(如 非凡M3U8)：from 字段为 "来源名$来源标识"。
    """
    if not play_url:
        return []
    # 处理 "来源名$来源标识" 的 from 字段
    if play_from and "$" in play_from:
        play_from = play_from.split("$")[-1]
    episodes = []
    # 先按 # 或 $$$ 拆出各集片段
    if "$$$" in str(play_url):
        parts = str(play_url).split("$$$")
    else:
        parts = str(play_url).split("#")
    for item in parts:
        item = item.strip()
        if not item:
            continue
        if "$" in item:
            name, url = item.split("$", 1)
            episodes.append({"name": name.strip(), "url": url.strip()})
        else:
            episodes.append({"name": f"第{len(episodes)+1}集", "url": item.strip()})
    return episodes


def fetch_json(api, page, headers):
    r = requests.get(api, params={"pg": page},
                     headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()
    # 兼容 {code:1, list:[...]} 与直接 {list:[...]}
    items = data.get("list") or data.get("data") or []
    return items, data.get("pagecount") or data.get("pageCount")


def fetch_xml(api, page, headers):
    r = requests.get(api, params={"pg": page},
                     headers=headers, timeout=30)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    items = []
    for v in root.iter("list") if list(root) and root.find("list") is not None else root:
        pass
    # 标准结构 <list><vod><id>..</vod>...</list>
    pagecount = None
    for node in root:
        if node.tag == "pagecount":
            pagecount = node.text
        if node.tag in ("list", "video", "vod"):
            for vod in node:
                d = {child.tag: (child.text or "") for child in vod}
                # XML 接口返回小写字段，标准化为 vod_ 前缀
                d = _normalize_xml_item(d)
                if d.get("vod_name"):
                    items.append(d)
    return items, pagecount


def _normalize_xml_item(d):
    """把苹果CMS XML 接口的小写字段标准化为 vod_ 前缀（与JSON一致）。"""
    key_map = {
        "id": "vod_id", "name": "vod_name", "type": "type_name",
        "note": "vod_remarks", "pic": "vod_pic", "pic_thumb": "vod_pic_thumb",
        "area": "vod_area", "lang": "vod_lang", "year": "vod_year",
        "director": "vod_director", "actor": "vod_actor", "content": "vod_content",
        "play_from": "vod_play_from", "play_url": "vod_play_url",
        "dt": "vod_play_from", "time": "vod_time",
    }
    out = {}
    for k, v in d.items():
        out[key_map.get(k, k)] = v
    # XML 的 dt 即播放源标识（逗号或$$$分隔）
    if "vod_play_from" in out and not out.get("vod_play_from"):
        out["vod_play_from"] = d.get("dt", "")
    return out


class Command(BaseCommand):
    help = "采集苹果CMS provide/vod 接口数据"

    def add_arguments(self, parser):
        parser.add_argument("--api", required=True, help="采集接口地址")
        parser.add_argument("--at", choices=["auto", "json", "xml"], default="auto",
                            help="返回格式（默认auto自动识别）")
        parser.add_argument("--pages", type=int, default=3, help="采集页数")
        parser.add_argument("--from", dest="from_flag", default="", help="仅采集指定来源")
        parser.add_argument("--reset-categories", action="store_true",
                            help="同步分类时清空旧分类映射")
        parser.add_argument("--headers", default="", help="额外请求头(JSON)")
        parser.add_argument("--detail", action="store_true",
                            help="列表采集后逐个请求detail接口补齐播放数据")
        parser.add_argument("--detail-api", default="",
                            help="detail接口地址（默认用 --api；若列表为xml而detail需json请单独指定）")

    # 苹果CMS type_name → 站点分类树 的映射规则
    TYPE_TO_ROOT = {
        # 含"片"或电影相关 → 电影
        "movie": "电影",
        # 含"剧" → 电视剧
        "tv": "电视剧",
        # 含"动漫/动画" → 动漫
        "anime": "动漫",
        # 含"综艺/娱乐" → 电影(或独立，这里归电影)
        "variety": "电影",
        "doc": "电影",
    }

    def _map_category(self, type_name):
        """把苹果CMS的 type_name 映射到站点二级分类。找不到则归一级电影。"""
        from videos.models import Category
        t = (type_name or "").strip()
        if not t:
            return None
        # 短剧
        if "短剧" in t:
            return Category.objects.filter(name="短剧", parent__isnull=True).first()
        # 精确匹配二级分类（动漫子类/电视剧子类/电影子类）
        cat = Category.objects.filter(name=t).exclude(parent__isnull=True).first()
        if cat:
            return cat
        # 规则匹配 → 归一级
        if "动漫" in t or "动画" in t:
            root = "动漫"
        elif "剧" in t:
            root = "电视剧"
        else:
            root = "电影"
        return Category.objects.filter(name=root, parent__isnull=True).first()

    # 常见来源标识 → 显示名
    SOURCE_NAMES = {
        "feifan": "非凡线路",
        "ffm3u8": "非凡M3U8",
        "ffzy": "非凡资源",
        "youku": "优酷",
        "qiyi": "爱奇艺",
        "qq": "腾讯视频",
        "mgtv": "芒果TV",
        "bilibili": "哔哩哔哩",
        "sohu": "搜狐",
        "letv": "乐视",
        "1905": "1905电影",
        "default": "默认线路",
    }

    def _source_name(self, flag):
        return self.SOURCE_NAMES.get(flag, flag)

    def _fetch_detail(self, api, vod_id, headers):
        """请求 detail 接口拿完整播放数据（统一用 json，json detail 才返回播放地址）。"""
        try:
            r = requests.get(api, params={"ac": "detail", "ids": vod_id},
                             headers=headers, timeout=30)
            r.raise_for_status()
            data = r.json()
            items = data.get("list") or data.get("data") or []
            return items[0] if items else None
        except Exception as e:  # noqa: BLE001
            self.stderr.write(self.style.WARNING(f"detail {vod_id} 失败: {e}"))
            return None

    @transaction.atomic
    def handle(self, *args, **opts):
        api = opts["api"]
        at = opts["at"]
        pages = opts["pages"]
        from_flag = opts["from_flag"]
        use_detail = opts["detail"]
        detail_api = opts["detail_api"] or api
        # detail 用 json 格式（json detail 才返回播放地址）
        detail_at = "json"

        headers = {"User-Agent": "Mozilla/5.0 (film-collector)"}
        if opts["headers"]:
            try:
                headers.update(json.loads(opts["headers"]))
            except json.JSONDecodeError:
                raise CommandError("--headers 必须是合法JSON")

        if at == "auto":
            at = "xml" if "at/xml" in api or "at=/" in api or "xml" in api.lower() else "json"

        total_new = total_upd = total_cat = total_src = 0
        for page in range(1, pages + 1):
            try:
                if at == "xml":
                    items, pagecount = fetch_xml(api, page, headers)
                else:
                    items, pagecount = fetch_json(api, page, headers)
            except Exception as e:  # noqa: BLE001
                self.stderr.write(self.style.WARNING(f"第{page}页失败: {e}"))
                continue

            if not items:
                break
            self.stdout.write(f"[第{page}页] 读取 {len(items)} 条")

            for item in items:
                title = (item.get("vod_name") or "").strip()
                if not title:
                    continue

                # 若列表无播放数据且开启 detail，则补齐
                if use_detail and not (item.get("vod_play_url") or ""):
                    vod_id = item.get("vod_id")
                    if vod_id:
                        d = self._fetch_detail(detail_api, vod_id, headers)
                        if d:
                            item.update(d)

                # 播放源解析
                play_from = (item.get("vod_play_from") or "").strip()
                play_url = (item.get("vod_play_url") or "").strip()
                if from_flag and play_from and from_flag not in play_from.split("$$$"):
                    # 指定来源：从组合里筛出该来源
                    continue

                # 分类：映射到站点分类树
                type_name = (item.get("type_name") or "").strip() or "未分类"
                cat = self._map_category(type_name)
                if cat is None:
                    cat = Category.objects.filter(name="电影", parent__isnull=True).first()
                total_cat += 1

                # 主片
                video, created = Video.objects.get_or_create(
                    title=title,
                    defaults={
                        "category": cat,
                        "video_type": self._map_type(type_name),
                        "year": (item.get("vod_year") or "")[:10],
                        "area": item.get("vod_area") or "",
                        "director": item.get("vod_director") or "",
                        "actors": item.get("vod_actor") or "",
                        "description": item.get("vod_content") or "",
                        "poster": item.get("vod_pic") or "",
                        "remark": item.get("vod_remarks") or "",
                        "status": "ended" if (item.get("vod_remarks") or "").find("更新") == -1 else "ongoing",
                    },
                )
                if created:
                    total_new += 1
                else:
                    total_upd += 1
                    if video.category_id != cat.id:
                        video.category = cat
                    if item.get("vod_pic"):
                        video.poster = item["vod_pic"]
                    if item.get("vod_actor"):
                        video.actors = item["vod_actor"]
                    if item.get("vod_director"):
                        video.director = item["vod_director"]
                    video.save()

                # 播放源：按 from 拆分多条
                froms = [x for x in play_from.split("$$$") if x] or ["default"]
                urls = [x for x in play_url.split("$$$") if x] if play_url else []
                for i, f in enumerate(froms):
                    flag = f.split("$")[-1] if "$" in f else f
                    fname = f.split("$")[0] if "$" in f else self._source_name(f)
                    ep_data = urls[i] if i < len(urls) else ""
                    episodes = parse_play_data(f, ep_data)
                    src, _ = VideoSource.objects.update_or_create(
                        video=video, from_flag=flag,
                        defaults={"name": fname, "sort": i, "episodes": episodes},
                    )
                    total_src += 1

        self.stdout.write(self.style.SUCCESS(
            f"完成：新增{total_new}部 / 更新{total_upd}部 / 分类{total_cat}个 / 播放源{total_src}条"
        ))

    def _map_type(self, type_name):
        t = type_name.lower()
        if any(k in t for k in ("电影", "片")):
            return "movie"
        if any(k in t for k in ("剧", "连续")):
            return "tv"
        if any(k in t for k in ("综艺", "娱乐")):
            return "variety"
        if any(k in t for k in ("动漫", "动画")):
            return "anime"
        if any(k in t for k in ("纪录", "记录")):
            return "doc"
        return "movie"
