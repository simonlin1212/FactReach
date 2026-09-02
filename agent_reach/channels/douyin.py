# -*- coding: utf-8 -*-
"""Douyin single-link metadata and playback URL resolver."""

from __future__ import annotations

import json
import re
from urllib.parse import urljoin

import requests

from agent_reach.utils.url import host_matches, normalize_public_http_url

from .base import Channel

_DOUYIN_DOMAINS = ("douyin.com", "iesdouyin.com")
_MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
    "Mobile/15E148 Safari/604.1"
)
_MAX_SHARE_PAGE_BYTES = 5 * 1024 * 1024
_URL_RE = re.compile(r"https?://[^\s]+", re.IGNORECASE)
_VIDEO_ID_RE = re.compile(r"/(?:video|note)/(\d+)")
_ROUTER_DATA_RE = re.compile(
    r"window\._ROUTER_DATA\s*=\s*(\{.*?\})\s*;?\s*</script>",
    re.DOTALL,
)
_MAX_REDIRECTS = 5


class DouyinResolveError(RuntimeError):
    """Raised when a Douyin share link cannot be resolved safely."""


def _extract_share_url(share_text: str) -> str:
    for match in _URL_RE.findall(str(share_text or "")):
        candidate = match.rstrip("。，,;；!！?？)）]】'\"")
        if host_matches(candidate, *_DOUYIN_DOMAINS):
            return candidate
    raise DouyinResolveError("未找到有效的抖音分享链接")


def _first_aweme(payload) -> dict | None:
    if not isinstance(payload, dict):
        return None
    details = payload.get("aweme_details")
    if isinstance(details, list) and details and isinstance(details[0], dict):
        return details[0]
    return None


def _first_public_url(values) -> str | None:
    if not isinstance(values, list):
        return None
    for value in values:
        if not isinstance(value, str) or not value:
            continue
        try:
            return normalize_public_http_url(value)
        except ValueError:
            continue
    return None


def _extract_image_urls(item: dict) -> list[str]:
    """Extract stable image candidates from known Douyin note shapes."""
    images = item.get("images")
    if not isinstance(images, list):
        return []
    output: list[str] = []
    for image in images:
        if not isinstance(image, dict):
            continue
        candidates = [image.get("url_list")]
        for key in ("display_image", "origin_image", "download_url"):
            nested = image.get(key)
            if isinstance(nested, dict):
                candidates.append(nested.get("url_list"))
            elif isinstance(nested, str):
                candidates.append([nested])
        resolved = next(
            (url for values in candidates if (url := _first_public_url(values))),
            None,
        )
        if resolved and resolved not in output:
            output.append(resolved)
    return output


def _item_from_router_html(body: bytes) -> dict:
    html = body.decode("utf-8", errors="replace")
    match = _ROUTER_DATA_RE.search(html)
    if match is None:
        raise DouyinResolveError("抖音分享页未包含可解析的视频信息")
    try:
        router_data = json.loads(match.group(1))
        loader_data = router_data["loaderData"]
        page_data = loader_data.get("video_(id)/page") or loader_data.get(
            "note_(id)/page"
        )
        item = page_data["videoInfoRes"]["item_list"][0]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise DouyinResolveError("抖音视频信息结构无法识别") from exc
    if not isinstance(item, dict):
        raise DouyinResolveError("抖音视频信息结构无法识别")
    return item


def _read_limited(response) -> bytes:
    """Read at most the configured response cap without eager buffering."""
    length = response.headers.get("Content-Length") if response.headers else None
    if length:
        try:
            if int(length) > _MAX_SHARE_PAGE_BYTES:
                raise DouyinResolveError("抖音分享页响应过大")
        except ValueError:
            pass

    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_content(chunk_size=64 * 1024):
        if not chunk:
            continue
        total += len(chunk)
        if total > _MAX_SHARE_PAGE_BYTES:
            raise DouyinResolveError("抖音分享页响应过大")
        chunks.append(chunk)
    return b"".join(chunks)


def _resolve_redirect_url(share_url: str, headers: dict[str, str]) -> str:
    """Follow only bounded Douyin redirects without downloading response bodies."""
    current = share_url
    for _ in range(_MAX_REDIRECTS + 1):
        response = None
        try:
            response = requests.get(
                current,
                headers=headers,
                timeout=15,
                stream=True,
                allow_redirects=False,
            )
            response.raise_for_status()
            status = response.status_code
            location = response.headers.get("Location") if response.headers else None
            if isinstance(status, int) and 300 <= status < 400 and location:
                next_url = urljoin(current, location)
                if not host_matches(next_url, *_DOUYIN_DOMAINS):
                    raise DouyinResolveError(
                        "抖音分享链接重定向到了非抖音域名"
                    )
                current = next_url
                continue

            # Real requests with redirects disabled retain ``current`` here.
            # Keeping response.url supports custom transports and test doubles.
            final_url = str(response.url or current)
            if not host_matches(final_url, *_DOUYIN_DOMAINS):
                raise DouyinResolveError(
                    "抖音分享链接重定向到了非抖音域名"
                )
            return final_url
        except requests.RequestException as exc:
            raise DouyinResolveError(f"抖音分享链接解析失败: {exc}") from exc
        finally:
            if response is not None:
                response.close()
    raise DouyinResolveError("抖音分享链接重定向次数过多")


class DouyinChannel(Channel):
    name = "douyin"
    description = "抖音视频/图文解析与文案"
    backends = ["内置分享页解析"]
    tier = 0

    def can_handle(self, url: str) -> bool:
        return host_matches(url, *_DOUYIN_DOMAINS)

    def check(self, config=None):
        self.active_backend = self.backends[0]
        return (
            "ok",
            "内置解析抖音视频/图文分享链接、发布文案、作者、播放或图片地址；"
            "无需登录或 API Key",
        )

    def resolve(self, share_text: str) -> dict[str, object]:
        """Resolve one video or note share URL into stable metadata."""
        share_url = _extract_share_url(share_text)
        headers = {"User-Agent": _MOBILE_UA, "Accept": "text/html,*/*"}
        final_url = _resolve_redirect_url(share_url, headers)
        video_match = _VIDEO_ID_RE.search(final_url)
        if video_match is None:
            video_match = _VIDEO_ID_RE.search(share_url)
        if video_match is None:
            raise DouyinResolveError("无法从抖音链接中解析视频 ID")
        video_id = video_match.group(1)
        share_kind = "note" if "/note/" in final_url else "video"

        item = None
        api_base = "https://www.iesdouyin.com/web/api/v2/aweme/slidesinfo/"
        api_urls = (
            f"{api_base}?aweme_ids=%5B{video_id}%5D",
            f"{api_base}?aweme_ids=%5B{video_id}%5D&request_source=200",
        )
        for api_url in api_urls:
            api_response = None
            try:
                api_response = requests.get(
                    api_url, headers=headers, timeout=15, stream=True
                )
                api_response.raise_for_status()
                body = _read_limited(api_response)
            except (requests.RequestException, DouyinResolveError):
                continue
            finally:
                if api_response is not None:
                    api_response.close()
            try:
                item = _first_aweme(json.loads(body))
            except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
                item = None
            if item is not None:
                break

        if item is None:
            page_url = (
                f"https://www.iesdouyin.com/share/{share_kind}/{video_id}/"
            )
            page = None
            try:
                page = requests.get(
                    page_url, headers=headers, timeout=15, stream=True
                )
                page.raise_for_status()
                body = _read_limited(page)
            except requests.RequestException as exc:
                raise DouyinResolveError(f"抖音分享页读取失败: {exc}") from exc
            finally:
                if page is not None:
                    page.close()
            item = _item_from_router_html(body)

        author = item.get("author")
        nickname = author.get("nickname", "") if isinstance(author, dict) else ""
        metadata: dict[str, object] = {
            "video_id": video_id,
            "description": str(item.get("desc", "")).strip(),
            "author": str(nickname).strip(),
        }
        image_urls = _extract_image_urls(item)
        if share_kind == "note" or (image_urls and not item.get("video")):
            if not image_urls:
                raise DouyinResolveError("抖音图文作品没有可解析的图片地址")
            return {
                "video_id": video_id,
                "content_type": "note",
                "description": metadata["description"],
                "author": metadata["author"],
                "image_urls": image_urls,
            }

        try:
            play_urls = item["video"]["play_addr"]["url_list"]
            play_url = _first_public_url(play_urls)
        except (KeyError, TypeError) as exc:
            raise DouyinResolveError("抖音视频信息结构无法识别") from exc
        if play_url is None:
            raise DouyinResolveError("抖音播放地址不是公开 HTTP(S) URL")
        return {
            "video_id": video_id,
            "content_type": "video",
            "description": metadata["description"],
            "author": metadata["author"],
            "play_url": play_url,
        }

    def transcribe(
        self,
        share_text: str,
        *,
        provider: str = "auto",
        allow_provider_fallback: bool = False,
        config=None,
    ) -> dict[str, object]:
        """Resolve a video and add spoken-word text via existing ASR routing."""
        from agent_reach.transcribe import transcribe

        result = self.resolve(share_text)
        if result.get("content_type") != "video":
            raise DouyinResolveError("抖音图文作品没有可转写的视频音轨")
        play_url = result.get("play_url")
        if not isinstance(play_url, str):
            raise DouyinResolveError("抖音视频信息结构无法识别")
        result["transcript"] = transcribe(
            play_url,
            provider=provider,
            config=config,
            allow_provider_fallback=allow_provider_fallback,
        )
        return result
