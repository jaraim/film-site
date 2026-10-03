# -*- coding: utf-8 -*-
"""影视站视图：首页 / 分类 / 详情 / 播放 / 搜索。"""
from django.contrib import messages
from django.db.models import Q, Count
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_GET

from .models import Video, Category


def _base_context():
    from system.services import get_ads_map
    from system.models import SiteConfig
    cfg = {c.key: c.value for c in SiteConfig.objects.all()}
    return {
        "categories": Category.objects.filter(parent__isnull=True),
        "type_choices": Video.TYPE_CHOICES,
        "ads_map": get_ads_map(),
        "site_name": cfg.get("site_name", "极简影视"),
        "site_footer": cfg.get("site_footer", ""),
        "site_logo": cfg.get("site_logo", ""),
    }


def home(request):
    """首页：按类型展示最近更新。"""
    ctx = _base_context()
    ctx["latest"] = Video.objects.filter(is_active=True)[:24]
    ctx["banners"] = Video.objects.filter(is_active=True).order_by("-views")[:6]
    ctx["by_type"] = {}
    for value, label in Video.TYPE_CHOICES:
        ctx["by_type"][label] = (
            Video.objects.filter(is_active=True, video_type=value)[:12]
        )
    return render(request, "videos/home.html", ctx)


@require_GET
def category(request, slug):
    """分类页 + 筛选。一级分类聚合子类影片。"""
    cat = get_object_or_404(Category, slug=slug)
    children = list(cat.children.all())
    if cat.is_root:
        qs = Video.objects.filter(is_active=True, category__parent=cat)
    else:
        qs = Video.objects.filter(is_active=True, category=cat)
    vt = request.GET.get("type")
    year = request.GET.get("year")
    sort = request.GET.get("sort", "latest")
    sub = request.GET.get("sub")  # 二级分类 slug
    if sub:
        qs = qs.filter(category__slug=sub)
    if vt:
        qs = qs.filter(video_type=vt)
    if year:
        qs = qs.filter(year=year)
    if sort == "views":
        qs = qs.order_by("-views")
    else:
        qs = qs.order_by("-updated_at")
    ctx = _base_context()
    ctx.update({
        "cat": cat,
        "children": children,
        "current_sub": sub,
        "videos": qs[:100],
        "years": Video.objects.filter(category__in=[c for c in children] or [cat]).values_list("year", flat=True).distinct()[:15],
        "current_type": vt,
        "current_year": year,
        "current_sort": sort,
    })
    return render(request, "videos/category.html", ctx)


def detail(request, pk):
    """详情页（含播放器容器）。"""
    video = get_object_or_404(Video, pk=pk, is_active=True)
    video.views += 1
    video.save(update_fields=["views"])
    ctx = _base_context()
    ctx.update({
        "video": video,
        "sources": video.source_list(),
        "related": (
            Video.objects.filter(is_active=True, category=video.category)
            .exclude(pk=video.pk)[:10]
        ),
    })
    return render(request, "videos/detail.html", ctx)


@require_GET
def play(request, pk):
    """播放页：加载播放器，URL 参数 ?from=线路标识&ep=第几集(1起)。"""
    video = get_object_or_404(Video, pk=pk, is_active=True)

    # ---- 付费片鉴权：need_points > 0 才需要积分 ----
    if video.need_points > 0:
        if not request.user.is_authenticated:
            messages.warning(request, "该影片需要积分观看，请先登录")
            return redirect(f"{reverse('member:login')}?next={request.path}")
        # 已解锁 → 放行
        from member.models import VideoAccess
        if not VideoAccess.objects.filter(user=request.user, video=video).exists():
            profile = request.user.profile
            if profile.points < video.need_points:
                return redirect(f"{reverse('member:center')}?need={video.pk}")
            # 扣费并解锁
            profile.points -= video.need_points
            profile.save(update_fields=["points"])
            from member.models import PointRecord
            PointRecord.objects.create(
                user=request.user, change_type="consume", delta=-video.need_points,
                balance=profile.points, note=f"观看《{video.title}》",
            )
            VideoAccess.objects.create(user=request.user, video=video)
            messages.success(request, f"已扣费 {video.need_points} 积分解锁本片")

    source_flag = request.GET.get("from") or (
        video.sources.first().from_flag if video.sources.exists() else ""
    )
    source = video.sources.filter(from_flag=source_flag).first()
    if not source:
        source = video.sources.first()
    if not source:
        return redirect(video.get_absolute_url())

    ep_no = int(request.GET.get("ep", "1") or 1)
    episodes = source.episode_list()
    ep_no = max(1, min(ep_no, len(episodes))) if episodes else 1
    episode = episodes[ep_no - 1] if episodes else (0, "", "")

    # 该片全部线路（供资源切换）
    sources = list(video.source_list())
    sources_data = [
        {
            "flag": s.from_flag,
            "name": s.name,
            "episodes": [{"n": i + 1, "name": e[1], "url": e[2]}
                         for i, e in enumerate(s.episode_list())],
        }
        for s in sources
    ]

    ctx = _base_context()
    from system.services import get_player_config
    ctx.update({
        "video": video,
        "sources": sources,
        "current_flag": source.from_flag,
        "episode": episode,
        "ep_no": ep_no,
        "total_eps": len(episodes),
        "sources_data_json": __import__("json").dumps(sources_data, ensure_ascii=False),
        "player_config_json": __import__("json").dumps(get_player_config(), ensure_ascii=False),
    })
    return render(request, "videos/play.html", ctx)


@require_GET
def search(request):
    """搜索：标题/导演/演员模糊匹配。"""
    kw = request.GET.get("q", "").strip()
    results = []
    if kw:
        results = (
            Video.objects.filter(is_active=True)
            .filter(Q(title__icontains=kw) | Q(director__icontains=kw) | Q(actors__icontains=kw))
            .order_by("-updated_at")[:60]
        )
    ctx = _base_context()
    ctx.update({"kw": kw, "results": results})
    return render(request, "videos/search.html", ctx)
