# -*- coding: utf-8 -*-
"""Web — Jina first, optional Firecrawl, explicit real-Chrome fallback."""

import urllib.request

from agent_reach.backends.browser_harness import (
    BrowserHarnessError,
    browser_harness_read,
)
from agent_reach.backends.firecrawl import (
    FirecrawlError,
    firecrawl_scrape,
    firecrawl_status,
)
from agent_reach.config import Config
from agent_reach.utils.url import normalize_public_http_url

from .base import Channel

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
_MAX_RESPONSE_BYTES = 5 * 1024 * 1024
_ANTIBOT_SCAN_BYTES = 4096


def _is_antibot_page(body: bytes) -> bool:
    """Recognize high-confidence Jina/Cloudflare challenge responses."""
    sample = body[:_ANTIBOT_SCAN_BYTES].decode("utf-8", errors="ignore").casefold()

    jina_captcha_warning = "warning:" in sample and "requiring captcha" in sample
    challenge_structure = any(
        marker in sample
        for marker in (
            "title: just a moment...",
            "## performing security verification",
            "title: attention required! | cloudflare",
        )
    )
    cloudflare_block = "title: attention required! | cloudflare" in sample and (
        "ray id" in sample or "/cdn-cgi/challenge-platform/" in sample
    )
    return (jina_captcha_warning and challenge_structure) or cloudflare_block


class WebChannel(Channel):
    name = "web"
    description = "任意网页"
    backends = ["Jina Reader", "Firecrawl", "browser-harness"]
    tier = 0

    def can_handle(self, url: str) -> bool:
        return True  # Fallback — handles any URL

    def check(self, config=None):
        # 恒可用兜底渠道：无本地命令、不做网络探测（doctor 已有多个渠道触网），保持零开销
        self.active_backend = self.backends[0]
        return (
            "ok",
            "Jina Reader 零鉴权读取；Firecrawl 可选动态抓取；"
            "browser-harness 仅在显式授权后连接真实 Chrome",
        )

    def _read_jina(self, url: str) -> str:
        """Read one page through Jina Reader."""
        url = normalize_public_http_url(url)
        jina_url = f"https://r.jina.ai/{url}"
        req = urllib.request.Request(
            jina_url,
            headers={"User-Agent": _UA, "Accept": "text/plain"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read(_MAX_RESPONSE_BYTES + 1)
        if len(body) > _MAX_RESPONSE_BYTES:
            raise ValueError(
                f"Jina Reader response exceeds {_MAX_RESPONSE_BYTES} byte limit"
            )
        if _is_antibot_page(body):
            raise RuntimeError(
                "Jina Reader 返回了反爬验证页，未获取到目标内容；"
                "请改用站点专用工具或浏览器读取"
            )
        return body.decode("utf-8")

    def read(
        self,
        url: str,
        *,
        config=None,
        backend: str = "auto",
        allow_browser: bool = False,
    ) -> str:
        """Read a public page with ordered, least-privilege fallbacks.

        ``browser-harness`` is never selected implicitly unless the caller
        sets ``allow_browser=True``. That explicit flag is the authorization
        boundary for opening the user's real, potentially logged-in Chrome.
        """
        target = normalize_public_http_url(url)
        normalized_backend = backend.strip().lower()
        aliases = {
            "auto": "auto",
            "jina": "jina",
            "jina reader": "jina",
            "firecrawl": "firecrawl",
            "browser": "browser-harness",
            "browser-harness": "browser-harness",
        }
        selected = aliases.get(normalized_backend)
        if selected is None:
            raise ValueError(
                "backend must be auto, jina, firecrawl, or browser-harness"
            )
        if selected == "jina":
            return self._read_jina(target)
        if selected == "firecrawl":
            return firecrawl_scrape(target, config=config)
        if selected == "browser-harness":
            return browser_harness_read(target)

        try:
            return self._read_jina(target)
        except (OSError, RuntimeError, ValueError) as jina_error:
            resolved_config = config or Config(read_only=True)
            firecrawl_error = None
            if firecrawl_status(resolved_config).configured:
                try:
                    return firecrawl_scrape(target, config=resolved_config)
                except (FirecrawlError, OSError) as exc:
                    firecrawl_error = exc
            if allow_browser:
                try:
                    return browser_harness_read(target)
                except BrowserHarnessError as browser_error:
                    if firecrawl_error is not None:
                        raise RuntimeError(
                            f"Firecrawl 失败：{firecrawl_error}；"
                            f"browser-harness 失败：{browser_error}"
                        ) from browser_error
                    raise
            if firecrawl_error is not None:
                raise FirecrawlError(
                    f"{firecrawl_error}（Jina Reader 同时失败：{jina_error}）"
                ) from firecrawl_error
            raise RuntimeError(
                f"{jina_error}；如页面需要登录或交互，请显式设置 "
                "allow_browser=True 或选择 backend='browser-harness'"
            ) from jina_error
