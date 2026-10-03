# -*- coding: utf-8 -*-
"""后台网页采集视图（需 staff 权限，供管理员在 /admin/collect/ 使用）。"""
import io
import json

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.shortcuts import render

from .management.commands.collect import Command as CollectCommand


@staff_member_required
def collect_view(request):
    """采集页面：表单 + 执行 + 结果展示。"""
    result = None
    stdout = None
    stderr = None

    if request.method == "POST":
        # 从表单收集参数
        api = request.POST.get("api", "").strip()
        at = request.POST.get("at", "auto")
        pages = int(request.POST.get("pages", "1") or 1)
        detail = request.POST.get("detail") == "on"
        from_flag = request.POST.get("from_flag", "").strip()
        detail_api = request.POST.get("detail_api", "").strip()

        if not api:
            stderr = "接口地址不能为空"
        else:
            # 实例化采集命令并运行，抓取输出
            cmd = CollectCommand()
            out_buf, err_buf = io.StringIO(), io.StringIO()
            try:
                cmd.stdout = out_buf
                cmd.stderr = err_buf
                cmd.handle(
                    api=api, at=at, pages=pages, from_flag=from_flag,
                    detail=detail, detail_api=detail_api, headers="",
                    reset_categories=False,
                )
                stdout = out_buf.getvalue()
                stderr = err_buf.getvalue()
                result = "成功"
            except Exception as e:  # noqa: BLE001
                stderr = f"采集出错：{e}\n{err_buf.getvalue()}"
                result = "失败"

    ctx = {
        "result": result,
        "stdout": stdout,
        "stderr": stderr,
        "presets": _presets(),
    }
    return render(request, "admin/collect.html", ctx)


def _presets():
    """常用采集源预设。"""
    return [
        {
            "name": "非凡资源 · 电影综合(json)",
            "api": "http://api.ffzyapi.com/api.php/provide/vod/at/json/",
        },
        {
            "name": "非凡资源 · 电影综合(xml)",
            "api": "http://api.ffzyapi.com/api.php/provide/vod/at/xml/",
        },
        {
            "name": "非凡资源 · M3U8线路(xml)",
            "api": "http://cj.ffzyapi.com/api.php/provide/vod/from/ffm3u8/at/xml/",
            "detail_api": "http://cj.ffzyapi.com/api.php/provide/vod/at/json/",
        },
    ]
