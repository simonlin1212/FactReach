# -*- coding: utf-8 -*-
"""Public WeChat article search and download via OpenCLI's browser bridge."""

from agent_reach.utils.url import host_matches

from .base import Channel


class WeChatPublicChannel(Channel):
    name = "wechat_public"
    description = "微信公众号公开文章"
    backends = ["OpenCLI Browser Bridge"]
    tier = 1
    domains = ("mp.weixin.qq.com", "weixin.sogou.com")
    usage = "opencli weixin search; opencli weixin download --url URL --output /tmp"

    def can_handle(self, url: str) -> bool:
        return host_matches(url, *self.domains)

    def check(self, config=None):
        from agent_reach.backends import (
            opencli_status,
            probe_opencli_wechat_adapter,
        )

        self.active_backend = None
        status = opencli_status()
        if not status.installed:
            return "off", (
                "公众号公开文章搜索不需公众号 Cookie，但需要 "
                "OpenCLI Browser Bridge。安装：\n"
                "  factreach install --system --channels wechat"
            )
        if status.broken:
            return "error", status.hint
        adapter = probe_opencli_wechat_adapter()
        if not adapter.ok:
            return "error", adapter.hint or "OpenCLI 缺少 weixin 适配器"
        if status.ready:
            return "warn", (
                "OpenCLI Browser Bridge 已连接；公众号搜索不需公众号 Cookie，"
                "但 Doctor 不主动发起搜索，当前未实搜验证。"
            )
        return "warn", status.hint
