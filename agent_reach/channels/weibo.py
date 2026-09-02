# -*- coding: utf-8 -*-
"""Weibo reading through OpenCLI with an explicit real-Chrome fallback."""

from agent_reach.backends.browser_harness import browser_harness_status
from agent_reach.utils.url import host_matches

from .base import Channel


class WeiboChannel(Channel):
    name = "weibo"
    description = "微博网页、搜索、用户动态与评论"
    backends = ["OpenCLI", "browser-harness"]
    tier = 1

    def can_handle(self, url: str) -> bool:
        return host_matches(url, "weibo.com", "weibo.cn")

    def check(self, config=None):
        from agent_reach.backends import (
            opencli_status,
            probe_opencli_weibo_adapter,
        )

        self.active_backend = None
        opencli = opencli_status()
        browser = browser_harness_status()
        adapter = (
            probe_opencli_weibo_adapter()
            if opencli.installed and not opencli.broken
            else None
        )
        if (
            opencli.installed
            and not opencli.broken
            and opencli.ready
            and adapter is not None
            and adapter.ok
        ):
            return (
                "warn",
                "OpenCLI 浏览器桥接已连接，但微博登录态和读取命令未实时执行；"
                "先在 Chrome 登录 weibo.com，再运行 `opencli weibo hot/search/post` 验证",
            )
        if browser.installed and browser.status != "error":
            diagnostic = (
                "browser-harness 已安装，可在明确授权后通过真实 Chrome 显式读取微博；"
                "Doctor 不连接标签页或检查登录态"
            )
            if opencli.installed and opencli.broken:
                diagnostic += f"；OpenCLI 后端异常：{opencli.hint}"
            elif adapter is not None and not adapter.ok:
                diagnostic += (
                    f"；OpenCLI 后端不可用：{adapter.hint or '缺少 weibo 适配器'}"
                )
            return (
                "warn",
                diagnostic,
            )
        if opencli.installed and opencli.broken:
            return "error", opencli.hint
        if adapter is not None and not adapter.ok:
            return "error", adapter.hint or "OpenCLI 缺少 weibo 适配器"
        if browser.status == "error":
            return "error", browser.hint
        if opencli.installed:
            return "warn", opencli.hint
        return (
            "off",
            "未安装微博后端。推荐 OpenCLI："
            "factreach install --system --channels weibo；"
            "可选 browser-harness：factreach install --system --channels browser-harness",
        )
