# -*- coding: utf-8 -*-
"""Tests for Douyin, Weibo, Firecrawl, and browser-harness integration."""

from __future__ import annotations

import base64
import ipaddress
import json
import socket
import subprocess
import urllib.parse
from unittest.mock import MagicMock, patch

import pytest
import requests

from agent_reach.backends.browser_harness import (
    BrowserHarnessError,
    _connect_public_host,
    _PinnedPublicProxy,
    _public_addresses,
    browser_harness_read,
    browser_harness_status,
)
from agent_reach.backends.firecrawl import (
    FirecrawlError,
    firecrawl_scrape,
    firecrawl_status,
)
from agent_reach.channels.douyin import DouyinChannel, DouyinResolveError
from agent_reach.channels.web import WebChannel
from agent_reach.channels.weibo import WeiboChannel


class _Config:
    def __init__(self, values=None):
        self.values = values or {}

    def get(self, key, default=None):
        return self.values.get(key, default)


def _http_response(*, url="https://example.com", body=b"", payload=None):
    response = MagicMock()
    response.url = url
    response.status_code = 200
    response.headers = {}
    response.content = body
    response.text = body.decode("utf-8", errors="replace")
    response.iter_content.side_effect = lambda chunk_size: iter(
        body[index : index + chunk_size]
        for index in range(0, len(body), chunk_size)
    )
    response.raise_for_status.return_value = None
    if payload is not None:
        response.json.return_value = payload
    return response


def _router_html(page_key="video_(id)/page"):
    item = {
        "desc": "Agent 搜索实测",
        "author": {"nickname": "Simon"},
        "video": {
            "play_addr": {
                "url_list": [
                    "https://v26-web.douyinvod.com/video/tos/example"
                ]
            }
        },
    }
    if page_key.startswith("note_"):
        item = {
            "desc": "Agent 搜索图文实测",
            "author": {"nickname": "Simon"},
            "images": [
                {
                    "url_list": [
                        "https://p3-sign.douyinpic.com/tos-cn-i/legacy-note"
                    ]
                }
            ],
        }
    payload = {
        "loaderData": {
            page_key: {
                "videoInfoRes": {
                    "item_list": [item]
                }
            }
        }
    }
    return (
        "<html><script>window._ROUTER_DATA = "
        + json.dumps(payload, ensure_ascii=False)
        + "</script></html>"
    ).encode("utf-8")


def _slides_payload():
    return {
        "aweme_details": [
            {
                "desc": "Agent 搜索实测",
                "author": {"nickname": "Simon"},
                "video": {
                    "play_addr": {
                        "url_list": [
                            "https://v26-web.douyinvod.com/video/tos/example"
                        ]
                    }
                },
            }
        ]
    }


def _note_payload():
    return {
        "aweme_details": [
            {
                "desc": "Agent 搜索图文实测",
                "author": {"nickname": "Simon"},
                "images": [
                    {
                        "url_list": [
                            "https://p3-sign.douyinpic.com/tos-cn-i/example-1"
                        ]
                    },
                    {
                        "display_image": {
                            "url_list": [
                                "https://p3-sign.douyinpic.com/tos-cn-i/example-2"
                            ]
                        }
                    },
                ],
            }
        ]
    }


class TestDouyinChannel:
    @pytest.mark.parametrize(
        "url",
        [
            "https://v.douyin.com/abc123/",
            "https://www.douyin.com/video/1234567890",
            "https://www.iesdouyin.com/share/video/1234567890/",
        ],
    )
    def test_can_handle_real_douyin_hosts(self, url):
        assert DouyinChannel().can_handle(url)

    @pytest.mark.parametrize(
        "url",
        [
            "https://douyin.com.evil.test/video/1",
            "https://example.com/?next=https://v.douyin.com/abc",
            "file:///tmp/video.mp4",
        ],
    )
    def test_rejects_non_douyin_hosts(self, url):
        assert not DouyinChannel().can_handle(url)

    def test_resolve_returns_description_author_and_play_url(self):
        redirect = _http_response(
            url="https://www.douyin.com/video/1234567890?previous_page=app_code_link"
        )
        api = _http_response(
            body=json.dumps(_slides_payload()).encode("utf-8"),
            payload=_slides_payload(),
        )

        with patch(
            "agent_reach.channels.douyin.requests.get",
            side_effect=[redirect, api],
        ) as mock_get:
            result = DouyinChannel().resolve("复制口令 https://v.douyin.com/abc123/ 打开抖音")

        assert result == {
            "video_id": "1234567890",
            "content_type": "video",
            "description": "Agent 搜索实测",
            "author": "Simon",
            "play_url": "https://v26-web.douyinvod.com/video/tos/example",
        }
        assert mock_get.call_count == 2
        assert mock_get.call_args_list[0].kwargs["timeout"] == 15
        assert "/web/api/v2/aweme/slidesinfo/" in mock_get.call_args_list[1].args[0]

    def test_resolve_falls_back_to_legacy_router_data(self):
        redirect = _http_response(url="https://www.douyin.com/video/1234567890")
        empty_api = _http_response(body=b'{"aweme_details":null}')
        empty_api.json.return_value = {"aweme_details": None}
        page = _http_response(body=_router_html())

        with patch(
            "agent_reach.channels.douyin.requests.get",
            side_effect=[redirect, empty_api, empty_api, page],
        ):
            result = DouyinChannel().resolve("https://v.douyin.com/abc123/")

        assert result["description"] == "Agent 搜索实测"
        assert result["content_type"] == "video"
        assert result["author"] == "Simon"

    def test_resolve_supports_douyin_note_pages(self):
        redirect = _http_response(url="https://www.douyin.com/note/1234567890")
        empty_api = _http_response(body=b'{"aweme_details":null}')
        empty_api.json.return_value = {"aweme_details": None}
        note_api = _http_response(
            body=json.dumps(_note_payload()).encode("utf-8"),
            payload=_note_payload(),
        )

        with patch(
            "agent_reach.channels.douyin.requests.get",
            side_effect=[redirect, empty_api, note_api],
        ):
            result = DouyinChannel().resolve("https://v.douyin.com/abc123/")

        assert result == {
            "video_id": "1234567890",
            "content_type": "note",
            "description": "Agent 搜索图文实测",
            "author": "Simon",
            "image_urls": [
                "https://p3-sign.douyinpic.com/tos-cn-i/example-1",
                "https://p3-sign.douyinpic.com/tos-cn-i/example-2",
            ],
        }

    def test_note_transcription_is_rejected_before_asr(self):
        channel = DouyinChannel()
        note = {
            "video_id": "1234567890",
            "content_type": "note",
            "description": "图文",
            "author": "Simon",
            "image_urls": ["https://example.com/one.jpg"],
        }
        with patch.object(channel, "resolve", return_value=note), patch(
            "agent_reach.transcribe.transcribe"
        ) as transcribe:
            with pytest.raises(DouyinResolveError, match="图文作品"):
                channel.transcribe("https://v.douyin.com/abc123/")
        transcribe.assert_not_called()

    def test_resolve_closes_failed_api_response_before_fallback(self):
        redirect = _http_response(url="https://www.douyin.com/video/1234567890")
        failed_api = _http_response()
        failed_api.raise_for_status.side_effect = requests.HTTPError("503")
        working_api = _http_response(
            body=json.dumps(_slides_payload()).encode("utf-8")
        )

        with patch(
            "agent_reach.channels.douyin.requests.get",
            side_effect=[redirect, failed_api, working_api],
        ):
            result = DouyinChannel().resolve("https://v.douyin.com/abc123/")

        assert result["video_id"] == "1234567890"
        failed_api.close.assert_called_once_with()

    def test_resolve_closes_oversized_api_and_tries_next_endpoint(self):
        redirect = _http_response(url="https://www.douyin.com/video/1234567890")
        oversized_api = _http_response(body=b"x" * (5 * 1024 * 1024 + 1))
        working_api = _http_response(
            body=json.dumps(_slides_payload()).encode("utf-8")
        )

        with patch(
            "agent_reach.channels.douyin.requests.get",
            side_effect=[redirect, oversized_api, working_api],
        ):
            result = DouyinChannel().resolve("https://v.douyin.com/abc123/")

        assert result["video_id"] == "1234567890"
        oversized_api.close.assert_called_once_with()

    def test_resolve_closes_failed_legacy_page_response(self):
        redirect = _http_response(url="https://www.douyin.com/video/1234567890")
        empty_api = _http_response(body=b'{"aweme_details":null}')
        failed_page = _http_response()
        failed_page.raise_for_status.side_effect = requests.HTTPError("503")

        with patch(
            "agent_reach.channels.douyin.requests.get",
            side_effect=[redirect, empty_api, empty_api, failed_page],
        ):
            with pytest.raises(DouyinResolveError, match="分享页读取失败"):
                DouyinChannel().resolve("https://v.douyin.com/abc123/")

        failed_page.close.assert_called_once_with()

    def test_note_legacy_fallback_uses_note_share_page(self):
        redirect = _http_response(url="https://www.douyin.com/note/1234567890")
        empty_api = _http_response(body=b'{"aweme_details":null}')
        empty_api.json.return_value = {"aweme_details": None}
        page = _http_response(body=_router_html("note_(id)/page"))

        with patch(
            "agent_reach.channels.douyin.requests.get",
            side_effect=[redirect, empty_api, empty_api, page],
        ) as mock_get:
            result = DouyinChannel().resolve("https://v.douyin.com/abc123/")

        assert result["description"] == "Agent 搜索图文实测"
        assert result["content_type"] == "note"
        assert mock_get.call_args_list[3].args[0] == (
            "https://www.iesdouyin.com/share/note/1234567890/"
        )

    def test_resolve_rejects_non_douyin_input_before_network(self):
        with patch("agent_reach.channels.douyin.requests.get") as mock_get:
            with pytest.raises(DouyinResolveError, match="抖音"):
                DouyinChannel().resolve("https://example.com/video/123")
        mock_get.assert_not_called()

    def test_resolve_rejects_redirect_away_from_douyin(self):
        redirect = _http_response(url="https://example.com/video/1234567890")
        with patch(
            "agent_reach.channels.douyin.requests.get", return_value=redirect
        ):
            with pytest.raises(DouyinResolveError, match="重定向"):
                DouyinChannel().resolve("https://v.douyin.com/abc123/")

    def test_resolve_rejects_oversized_share_page(self):
        redirect = _http_response(url="https://www.douyin.com/video/1234567890")
        empty_api = _http_response(body=b'{"aweme_details":null}')
        page = _http_response(body=b"x" * (5 * 1024 * 1024 + 1))
        with patch(
            "agent_reach.channels.douyin.requests.get",
            side_effect=[redirect, empty_api, empty_api, page],
        ):
            with pytest.raises(DouyinResolveError, match="过大"):
                DouyinChannel().resolve("https://v.douyin.com/abc123/")

    def test_check_is_zero_auth_and_built_in(self):
        channel = DouyinChannel()
        status, message = channel.check()
        assert status == "ok"
        assert channel.active_backend == "内置分享页解析"
        assert "无需登录" in message


class TestFirecrawlBackend:
    def test_status_requires_key_for_hosted_api(self):
        status = firecrawl_status(_Config())
        assert status.status == "off"
        assert "firecrawl-key" in status.hint

    def test_status_accepts_configured_key_without_network_probe(self):
        status = firecrawl_status(_Config({"firecrawl_api_key": "fc-test"}))
        assert status.status == "ok"
        assert status.configured

    def test_scrape_calls_v2_api_and_returns_markdown(self):
        config = _Config({"firecrawl_api_key": "fc-test"})
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            {"success": True, "data": {"markdown": "# Dynamic page\ncontent"}}
        ).encode("utf-8")

        with patch("urllib.request.urlopen", return_value=response) as mock_open:
            output = firecrawl_scrape("https://example.com/app", config=config)

        assert output == "# Dynamic page\ncontent"
        request = mock_open.call_args.args[0]
        assert request.full_url == "https://api.firecrawl.dev/v2/scrape"
        assert request.headers["Authorization"] == "Bearer fc-test"
        body = json.loads(request.data)
        assert body == {
            "url": "https://example.com/app",
            "formats": ["markdown"],
            "onlyMainContent": True,
        }

    def test_scrape_rejects_private_target_before_network(self):
        config = _Config({"firecrawl_api_key": "fc-test"})
        with patch("urllib.request.urlopen") as mock_open:
            with pytest.raises(ValueError, match="public HTTP"):
                firecrawl_scrape("http://127.0.0.1/admin", config=config)
        mock_open.assert_not_called()

    def test_scrape_rejects_missing_markdown(self):
        config = _Config({"firecrawl_api_key": "fc-test"})
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            {"success": True, "data": {}}
        ).encode("utf-8")
        with patch("urllib.request.urlopen", return_value=response):
            with pytest.raises(FirecrawlError, match="Markdown"):
                firecrawl_scrape("https://example.com", config=config)

    def test_scrape_wraps_transport_timeout(self):
        config = _Config({"firecrawl_api_key": "fc-test"})
        with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            with pytest.raises(FirecrawlError, match="timed out"):
                firecrawl_scrape("https://example.com", config=config)


class TestBrowserHarnessBackend:
    @staticmethod
    def _doh_response(payload):
        response = MagicMock()
        response.read.return_value = json.dumps(payload).encode("utf-8")
        response.__enter__.return_value = response
        return response

    def test_status_uses_side_effect_free_version_probe(self):
        with patch(
            "agent_reach.backends.browser_harness.probe_command"
        ) as probe:
            probe.return_value.status = "ok"
            probe.return_value.ok = True
            probe.return_value.output = "0.1.0"
            status = browser_harness_status()

        probe.assert_called_once_with(
            "browser-harness",
            ["--version"],
            timeout=10,
            package="git+https://github.com/browser-use/browser-harness.git",
        )
        assert status.status == "warn"
        assert status.installed
        assert "显式" in status.hint

    def test_read_passes_script_over_stdin_without_shell(self):
        payload = {
            "url": "https://example.com/dashboard",
            "title": "Dashboard",
            "text": "Account summary",
        }
        encoded = base64.b64encode(
            json.dumps(payload, ensure_ascii=False).encode("utf-8")
        ).decode("ascii")
        proc = subprocess.CompletedProcess(
            ["browser-harness"],
            0,
            f"noise\n__AGENT_REACH_RESULT__{encoded}\n",
            "",
        )

        with patch("subprocess.run", return_value=proc) as mock_run:
            output = browser_harness_read("https://example.com/dashboard")

        assert output == "Account summary"
        args, kwargs = mock_run.call_args_list[0]
        assert args[0] == ["browser-harness"]
        assert kwargs["shell"] is False
        assert "https://example.com/dashboard" in kwargs["input"]
        script = kwargs["input"]
        assert "new_tab()" not in script
        assert "Target.createTarget" in script
        assert "Target.createBrowserContext" in script
        assert "proxyServer=proxy_url" in script
        assert "proxyBypassList='<-loopback>'" in script
        assert "Storage.getCookies" in script
        assert "Storage.setCookies" in script
        assert "target_host" not in script
        assert "range(0, len(copied_cookies), 200)" in script
        assert "Target.attachToTarget" in script
        assert "session_id=sid" in script
        assert "Target.setAutoAttach" in script
        assert "Target.attachedToTarget" in script
        assert "Runtime.runIfWaitingForDebugger" in script
        assert "Fetch.enable" in script
        assert script.index("Fetch.enable") < script.index("location.assign")
        assert "guarded_sessions" in script
        assert "Target.disposeBrowserContext" in script
        assert "stable_samples" in script
        assert "selectedText || bodyText" in script
        cleanup_args, cleanup_kwargs = mock_run.call_args_list[1]
        assert cleanup_args[0] == ["browser-harness", "--reload"]
        assert cleanup_kwargs["env"]["BU_NAME"].startswith("factreach-")

    def test_public_dns_rejects_private_alias(self):
        private_answer = {
            "Status": 0,
            "Answer": [{"type": 1, "data": "127.0.0.1"}],
        }
        empty_answer = {"Status": 0, "Answer": []}
        responses = [
            self._doh_response(private_answer),
            self._doh_response(empty_answer),
        ]
        with patch("urllib.request.urlopen", side_effect=responses):
            with pytest.raises(ValueError, match="non-public address"):
                _public_addresses("127.0.0.1.nip.io")

    def test_public_connection_is_pinned_to_verified_numeric_address(self):
        connected = MagicMock()
        with (
            patch(
                "agent_reach.backends.browser_harness._public_addresses",
                return_value=(ipaddress.ip_address("93.184.216.34"),),
            ),
            patch("socket.create_connection", return_value=connected) as connect,
        ):
            result = _connect_public_host("example.com", 443)

        assert result is connected
        connect.assert_called_once_with(("93.184.216.34", 443), timeout=10)

    def test_pinned_proxy_rejects_loopback_connect(self):
        with _PinnedPublicProxy() as proxy:
            parsed = urllib.parse.urlsplit(proxy.url)
            with socket.create_connection((parsed.hostname, parsed.port), timeout=2) as client:
                client.sendall(
                    b"CONNECT 127.0.0.1:5931 HTTP/1.1\r\n"
                    b"Host: 127.0.0.1:5931\r\n\r\n"
                )
                response = client.recv(4096)

        assert response.startswith(b"HTTP/1.1 403 Forbidden")

    def test_read_rejects_private_target_before_process(self):
        with patch("subprocess.run") as mock_run:
            with pytest.raises(ValueError, match="public HTTP"):
                browser_harness_read("http://localhost/private")
        mock_run.assert_not_called()

    def test_read_blocks_private_final_redirect(self):
        payload = {
            "url": "http://127.0.0.1:8080/private",
            "title": "Private service",
            "text": "secret internal content",
        }
        encoded = base64.b64encode(
            json.dumps(payload, ensure_ascii=False).encode("utf-8")
        ).decode("ascii")
        proc = subprocess.CompletedProcess(
            ["browser-harness"],
            0,
            f"__AGENT_REACH_RESULT__{encoded}\n",
            "",
        )

        with patch("subprocess.run", return_value=proc):
            with pytest.raises(BrowserHarnessError, match="non-public destination"):
                browser_harness_read("https://example.com/redirect")

    def test_read_surfaces_process_failure(self):
        proc = subprocess.CompletedProcess(
            ["browser-harness"],
            1,
            "",
            "Traceback (most recent call last):\nRuntimeError: remote debugging disabled",
        )
        with patch("subprocess.run", return_value=proc):
            with pytest.raises(BrowserHarnessError, match="^RuntimeError: remote debugging"):
                browser_harness_read("https://example.com")


class TestWebBackendRouting:
    def test_explicit_firecrawl_backend(self):
        channel = WebChannel()
        with patch(
            "agent_reach.channels.web.firecrawl_scrape",
            return_value="# rendered",
        ) as scrape:
            output = channel.read(
                "https://example.com/app",
                config=_Config({"firecrawl_api_key": "fc-test"}),
                backend="firecrawl",
            )
        assert output == "# rendered"
        scrape.assert_called_once()

    def test_explicit_browser_backend(self):
        channel = WebChannel()
        with patch(
            "agent_reach.channels.web.browser_harness_read",
            return_value="rendered text",
        ) as read:
            assert (
                channel.read(
                    "https://example.com/app",
                    backend="browser-harness",
                )
                == "rendered text"
            )
        read.assert_called_once_with("https://example.com/app")

    def test_auto_falls_back_to_configured_firecrawl_after_jina_failure(self):
        channel = WebChannel()
        with patch.object(
            channel, "_read_jina", side_effect=RuntimeError("反爬验证页")
        ), patch(
            "agent_reach.channels.web.firecrawl_scrape",
            return_value="# rendered",
        ) as firecrawl, patch(
            "agent_reach.channels.web.browser_harness_read"
        ) as browser:
            result = channel.read(
                "https://example.com/app",
                config=_Config({"firecrawl_api_key": "fc-test"}),
            )

        assert result == "# rendered"
        firecrawl.assert_called_once()
        browser.assert_not_called()

    def test_auto_falls_back_to_firecrawl_after_jina_network_failure(self):
        channel = WebChannel()
        with patch.object(
            channel, "_read_jina", side_effect=OSError("temporary DNS failure")
        ), patch(
            "agent_reach.channels.web.firecrawl_scrape",
            return_value="# rendered after network failure",
        ):
            result = channel.read(
                "https://example.com/app",
                config=_Config({"firecrawl_api_key": "fc-test"}),
            )

        assert result == "# rendered after network failure"

    @pytest.mark.parametrize(
        "failure",
        [
            ValueError("Jina Reader response exceeds byte limit"),
            UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid byte"),
        ],
    )
    def test_auto_falls_back_after_jina_content_failure(self, failure):
        channel = WebChannel()
        with patch.object(channel, "_read_jina", side_effect=failure), patch(
            "agent_reach.channels.web.firecrawl_scrape",
            return_value="# rendered after content failure",
        ):
            result = channel.read(
                "https://example.com/app",
                config=_Config({"firecrawl_api_key": "fc-test"}),
            )

        assert result == "# rendered after content failure"

    def test_auto_never_opens_real_browser_without_explicit_permission(self):
        channel = WebChannel()
        with patch.object(
            channel, "_read_jina", side_effect=RuntimeError("反爬验证页")
        ), patch(
            "agent_reach.channels.web.firecrawl_scrape",
            side_effect=FirecrawlError("not configured"),
        ), patch(
            "agent_reach.channels.web.browser_harness_read"
        ) as browser:
            with pytest.raises(RuntimeError, match="allow_browser"):
                channel.read("https://example.com/app", config=_Config())

        browser.assert_not_called()

    def test_auto_can_use_browser_after_explicit_permission(self):
        channel = WebChannel()
        with patch.object(
            channel, "_read_jina", side_effect=RuntimeError("反爬验证页")
        ), patch(
            "agent_reach.channels.web.firecrawl_scrape",
            side_effect=FirecrawlError("not configured"),
        ), patch(
            "agent_reach.channels.web.browser_harness_read",
            return_value="logged-in content",
        ) as browser:
            result = channel.read(
                "https://example.com/account",
                config=_Config(),
                allow_browser=True,
            )

        assert result == "logged-in content"
        browser.assert_called_once()

    def test_auto_can_use_browser_after_firecrawl_transport_failure(self):
        channel = WebChannel()
        with patch.object(
            channel, "_read_jina", side_effect=RuntimeError("反爬验证页")
        ), patch(
            "agent_reach.channels.web.firecrawl_scrape",
            side_effect=TimeoutError("timed out"),
        ), patch(
            "agent_reach.channels.web.browser_harness_read",
            return_value="browser fallback",
        ):
            result = channel.read(
                "https://example.com/account",
                config=_Config({"firecrawl_api_key": "fc-test"}),
                allow_browser=True,
            )

        assert result == "browser fallback"

    def test_auto_preserves_firecrawl_failure_without_browser_permission(self):
        channel = WebChannel()
        with patch.object(
            channel, "_read_jina", side_effect=RuntimeError("反爬验证页")
        ), patch(
            "agent_reach.channels.web.firecrawl_scrape",
            side_effect=FirecrawlError("HTTP 401 invalid API key"),
        ):
            with pytest.raises(FirecrawlError, match="401 invalid API key"):
                channel.read(
                    "https://example.com/account",
                    config=_Config({"firecrawl_api_key": "fc-test"}),
                )


class TestWeiboChannel:
    def test_can_handle_weibo_urls_only(self):
        channel = WeiboChannel()
        assert channel.can_handle("https://weibo.com/123/statusid")
        assert channel.can_handle("https://www.weibo.com/123/statusid")
        assert not channel.can_handle("https://weibo.com.evil.test/123")

    def test_reports_off_when_no_backend_is_installed(self):
        channel = WeiboChannel()
        with patch("agent_reach.backends.opencli_status") as opencli, patch(
            "agent_reach.channels.weibo.browser_harness_status"
        ) as browser:
            opencli.return_value.installed = False
            browser.return_value.installed = False
            status, message = channel.check()

        assert status == "off"
        assert channel.active_backend is None
        assert "OpenCLI" in message
        assert "browser-harness" in message

    def test_browser_harness_is_an_explicit_fallback(self):
        channel = WeiboChannel()
        with patch("agent_reach.backends.opencli_status") as opencli, patch(
            "agent_reach.channels.weibo.browser_harness_status"
        ) as browser:
            opencli.return_value.installed = False
            browser.return_value.installed = True
            browser.return_value.hint = "installed"
            status, message = channel.check()

        assert status == "warn"
        assert channel.active_backend is None
        assert "显式" in message

    def test_browser_fallback_keeps_opencli_adapter_failure_visible(self):
        channel = WeiboChannel()
        with patch("agent_reach.backends.opencli_status") as opencli, patch(
            "agent_reach.backends.probe_opencli_weibo_adapter"
        ) as adapter, patch(
            "agent_reach.channels.weibo.browser_harness_status"
        ) as browser:
            opencli.return_value.installed = True
            opencli.return_value.broken = False
            opencli.return_value.ready = False
            adapter.return_value.ok = False
            adapter.return_value.hint = "OpenCLI 缺少公开适配器：weibo"
            browser.return_value.installed = True
            browser.return_value.status = "ok"
            status, message = channel.check()

        assert status == "warn"
        assert channel.active_backend is None
        assert "browser-harness" in message
        assert "weibo" in message

    def test_broken_browser_harness_is_not_reported_as_available(self):
        channel = WeiboChannel()
        with patch("agent_reach.backends.opencli_status") as opencli, patch(
            "agent_reach.channels.weibo.browser_harness_status"
        ) as browser:
            opencli.return_value.installed = False
            browser.return_value.installed = True
            browser.return_value.status = "error"
            browser.return_value.hint = "broken shim"
            status, message = channel.check()

        assert status == "error"
        assert message == "broken shim"

    def test_connected_opencli_requires_weibo_adapter(self):
        channel = WeiboChannel()
        with patch("agent_reach.backends.opencli_status") as opencli, patch(
            "agent_reach.backends.probe_opencli_weibo_adapter"
        ) as adapter, patch(
            "agent_reach.channels.weibo.browser_harness_status"
        ) as browser:
            opencli.return_value.installed = True
            opencli.return_value.broken = False
            opencli.return_value.ready = True
            adapter.return_value.ok = False
            adapter.return_value.hint = "OpenCLI 缺少公开适配器：weibo"
            browser.return_value.installed = False
            browser.return_value.status = "off"
            status, message = channel.check()

        assert status == "error"
        assert channel.active_backend is None
        assert "weibo" in message
