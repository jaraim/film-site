# -*- coding: utf-8 -*-
"""system 模块服务函数：读取广告与播放器配置。"""
from .models import AdSlot, Ad, PlayerConfig


def get_slot_ads(position):
    """按广告位位置返回启用广告列表（已渲染 HTML）。"""
    try:
        slot = AdSlot.objects.get(position=position, is_active=True)
    except AdSlot.DoesNotExist:
        return []
    ads = []
    for ad in slot.ads.filter(is_active=True).order_by("sort"):
        html = ad.render()
        if html:
            ads.append(html)
    return ads


def get_ads_map():
    """返回全部启用广告位的 {position: [html]}，供所有页面 context 注入。"""
    result = {}
    for slot in AdSlot.objects.filter(is_active=True):
        ads = get_slot_ads(slot.position)
        if ads:
            result[slot.position] = ads
    return result


def get_player_config():
    """返回播放器全局配置字典。"""
    config = {}
    for c in PlayerConfig.objects.all():
        config[c.key] = c.value
    # 默认值兜底
    defaults = {
        "default_rate": "1.0",
        "default_skip_intro": "0",
        "default_skip_outro": "0",
        "auto_next": "1",
    }
    for k, v in defaults.items():
        config.setdefault(k, v)
    return config
