# -*- coding: utf-8 -*-
"""Shared helper for OpenCLI adapters backed by public, zero-auth sources."""

from agent_reach.backends.opencli import probe_opencli_adapters
from agent_reach.utils.url import host_matches

from .base import Channel


class OpenCLIPublicChannel(Channel):
    """A public OpenCLI source that does not use the Chrome bridge."""

    domains: tuple[str, ...] = ()
    adapters: tuple[str, ...] = ()
    usage: str = ""

    backends = ["OpenCLI public"]
    tier = 0

    def can_handle(self, url: str) -> bool:
        return host_matches(url, *self.domains)

    def check(self, config=None):
        self.active_backend = None
        probe = probe_opencli_adapters(self.adapters)
        if probe.status == "missing":
            return "off", (
                f"{self.description}需要 OpenCLI 公开数据适配器。安装：\n"
                "  npm install -g @jackwener/opencli"
            )
        if probe.status == "broken":
            return "error", (
                "OpenCLI 命令存在但无法执行（Node.js 环境损坏）。重装：\n"
                "  npm install -g @jackwener/opencli"
            )
        if not probe.ok:
            return "error", f"OpenCLI 公开数据后端检查失败：{probe.hint or probe.status}"

        return "warn", (
            f"OpenCLI 公开数据运行时可执行（{self.usage}），无需 Cookie / Chrome 扩展；"
            "Doctor 不代发远端查询，实际任务仍须以非空 JSON 结果为成功依据"
        )
