# -*- coding: utf-8 -*-
"""Firecrawl hosted/self-hosted dynamic-page backend."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlsplit

from agent_reach.config import Config
from agent_reach.utils.url import normalize_public_http_url

_DEFAULT_API_URL = "https://api.firecrawl.dev/v2"
_MAX_RESPONSE_BYTES = 10 * 1024 * 1024


class FirecrawlError(RuntimeError):
    """Raised when Firecrawl cannot return usable page Markdown."""


@dataclass(frozen=True)
class FirecrawlStatus:
    status: str
    configured: bool
    hint: str


def _config_value(config, key: str, default=None):
    if config is None:
        config = Config(read_only=True)
    return config.get(key, default)


def _api_base(config=None) -> str:
    candidate = str(
        _config_value(config, "firecrawl_api_url", _DEFAULT_API_URL)
        or _DEFAULT_API_URL
    ).strip().rstrip("/")
    parsed = urlsplit(candidate)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise FirecrawlError("Firecrawl API URL must be a valid HTTP(S) endpoint")
    if parsed.scheme == "http" and parsed.hostname not in {
        "127.0.0.1",
        "::1",
        "localhost",
    }:
        raise FirecrawlError(
            "Firecrawl API URL must use HTTPS unless it is a loopback self-host"
        )
    return candidate


def firecrawl_status(config=None) -> FirecrawlStatus:
    """Report configuration only; never spend credits during doctor checks."""
    try:
        base = _api_base(config)
    except FirecrawlError as exc:
        return FirecrawlStatus("error", False, str(exc))
    key = str(_config_value(config, "firecrawl_api_key", "") or "").strip()
    if base == _DEFAULT_API_URL and not key:
        return FirecrawlStatus(
            "off",
            False,
            "Firecrawl 托管版需要密钥：factreach configure firecrawl-key",
        )
    mode = "托管 API" if base == _DEFAULT_API_URL else "自托管 API"
    return FirecrawlStatus(
        "ok",
        True,
        f"Firecrawl {mode} 已配置；Doctor 不发起请求、不消耗额度",
    )


def firecrawl_scrape(url: str, *, config=None, timeout: int = 90) -> str:
    """Render one public page through Firecrawl and return Markdown."""
    target = normalize_public_http_url(url)
    status = firecrawl_status(config)
    if not status.configured:
        raise FirecrawlError(status.hint)

    base = _api_base(config)
    key = str(_config_value(config, "firecrawl_api_key", "") or "").strip()
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    request = urllib.request.Request(
        f"{base}/scrape",
        data=json.dumps(
            {
                "url": target,
                "formats": ["markdown"],
                "onlyMainContent": True,
            }
        ).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(_MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise FirecrawlError(f"Firecrawl HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise FirecrawlError(f"Firecrawl request failed: {exc.reason}") from exc
    except (TimeoutError, OSError) as exc:
        raise FirecrawlError(f"Firecrawl request failed: {exc}") from exc

    if len(raw) > _MAX_RESPONSE_BYTES:
        raise FirecrawlError("Firecrawl response exceeds 10 MiB safety limit")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FirecrawlError("Firecrawl returned invalid JSON") from exc
    if not isinstance(payload, dict) or payload.get("success") is False:
        raise FirecrawlError("Firecrawl scrape failed")
    data = payload.get("data")
    markdown = data.get("markdown") if isinstance(data, dict) else None
    if not isinstance(markdown, str) or not markdown.strip():
        raise FirecrawlError("Firecrawl response did not contain Markdown")
    return markdown
