# -*- coding: utf-8 -*-
"""全局模板上下文：站点配置 + 广告位，所有页面可用。"""
from .services import get_ads_map
from .models import SiteConfig


def site_globals(request):
    cfg = {c.key: c.value for c in SiteConfig.objects.all()}
    return {
        "ads_map": get_ads_map(),
        "site_name": cfg.get("site_name", "极简影视"),
        "site_footer": cfg.get("site_footer", ""),
        "site_logo": cfg.get("site_logo", ""),
    }
