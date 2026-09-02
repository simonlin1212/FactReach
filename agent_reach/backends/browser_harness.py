# -*- coding: utf-8 -*-
"""Explicit real-Chrome reading through browser-harness."""

from __future__ import annotations

import base64
import ipaddress
import json
import os
import secrets
import select
import socket
import socketserver
import subprocess
import threading
import urllib.parse
import urllib.request
from dataclasses import dataclass
from types import TracebackType

from agent_reach.probe import probe_command
from agent_reach.utils.process import utf8_subprocess_env
from agent_reach.utils.url import normalize_public_http_url

BROWSER_HARNESS_PACKAGE = (
    "git+https://github.com/browser-use/browser-harness.git"
)
_RESULT_PREFIX = "__AGENT_REACH_RESULT__"
_MAX_TEXT_CHARS = 200_000
_DOH_URL = "https://cloudflare-dns.com/dns-query"
_BLOCKED_HOSTS = {
    "home.arpa",
    "instance-data",
    "internal",
    "lan",
    "local",
    "localdomain",
    "localhost",
    "metadata.google.internal",
}
_BLOCKED_SUFFIXES = (
    ".home.arpa",
    ".internal",
    ".lan",
    ".local",
    ".localdomain",
    ".localhost",
)


class BrowserHarnessError(RuntimeError):
    """Raised when the explicit real-browser read cannot complete."""


@dataclass(frozen=True)
class BrowserHarnessStatus:
    status: str
    installed: bool
    hint: str


def _public_addresses(host: str) -> tuple[ipaddress.IPv4Address | ipaddress.IPv6Address, ...]:
    """Resolve *host* through public DNS and return only globally routable IPs."""
    normalized_host = host.lower().rstrip(".")
    if normalized_host in _BLOCKED_HOSTS or normalized_host.endswith(
        _BLOCKED_SUFFIXES
    ):
        raise ValueError("non-public hostname")
    try:
        literal = ipaddress.ip_address(normalized_host)
    except ValueError:
        literal = None
    if literal is not None:
        if not literal.is_global:
            raise ValueError("non-public IP address")
        return (literal,)
    if "." not in normalized_host:
        raise ValueError("non-public hostname")

    pending = [normalized_host]
    seen: set[str] = set()
    addresses: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for _ in range(6):
        next_names: list[str] = []
        for name in pending:
            normalized = name.lower().rstrip(".")
            if normalized in seen:
                continue
            seen.add(normalized)
            for record_type in ("A", "AAAA"):
                query = urllib.parse.urlencode(
                    {"name": normalized, "type": record_type}
                )
                request = urllib.request.Request(
                    f"{_DOH_URL}?{query}",
                    headers={
                        "Accept": "application/dns-json",
                        "User-Agent": "factreach-browser-guard/1",
                    },
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    raw = response.read(65_537)
                if len(raw) > 65_536:
                    raise ValueError("public DNS response was too large")
                answer = json.loads(raw.decode("utf-8"))
                status = answer.get("Status")
                if status not in (0, 3):
                    raise ValueError(f"public DNS returned status {status}")
                for record in answer.get("Answer") or []:
                    if not isinstance(record, dict):
                        continue
                    value = str(record.get("data", "")).strip().rstrip(".")
                    if record.get("type") in (1, 28):
                        try:
                            addresses.append(ipaddress.ip_address(value))
                        except ValueError:
                            pass
                    elif record.get("type") == 5 and value:
                        next_names.append(value)
        if addresses:
            if not all(address.is_global for address in addresses):
                raise ValueError("public DNS returned a non-public address")
            return tuple(addresses)
        pending = next_names
        if not pending:
            break
    raise ValueError("public DNS returned no address")


def _connect_public_host(host: str, port: int) -> socket.socket:
    """Connect to a public-DNS result without asking the system resolver."""
    last_error: OSError | None = None
    for address in _public_addresses(host):
        try:
            return socket.create_connection((str(address), port), timeout=10)
        except OSError as exc:
            last_error = exc
    raise OSError(f"could not connect to verified public host: {last_error}")


def _relay_sockets(left: socket.socket, right: socket.socket) -> None:
    sockets = [left, right]
    while sockets:
        readable, _, _ = select.select(sockets, [], [], 30)
        if not readable:
            return
        for source in readable:
            data = source.recv(65_536)
            if not data:
                return
            destination = right if source is left else left
            destination.sendall(data)


class _PinnedProxyHandler(socketserver.BaseRequestHandler):
    """Minimal HTTP CONNECT proxy pinned to public-DNS address results."""

    def handle(self) -> None:
        self.request.settimeout(10)
        raw = bytearray()
        while b"\r\n\r\n" not in raw and len(raw) <= 65_536:
            chunk = self.request.recv(4096)
            if not chunk:
                return
            raw.extend(chunk)
        if len(raw) > 65_536 or b"\r\n\r\n" not in raw:
            self.request.sendall(b"HTTP/1.1 431 Request Header Fields Too Large\r\n\r\n")
            return
        header, remainder = bytes(raw).split(b"\r\n\r\n", 1)
        lines = header.split(b"\r\n")
        try:
            method_bytes, target_bytes, version = lines[0].split(b" ", 2)
            method = method_bytes.decode("ascii").upper()
            target = target_bytes.decode("ascii")
            if method == "CONNECT":
                parsed = urllib.parse.urlsplit(f"//{target}")
                host = parsed.hostname or ""
                port = parsed.port or 443
                upstream = _connect_public_host(host, port)
                with upstream:
                    self.request.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                    if remainder:
                        upstream.sendall(remainder)
                    _relay_sockets(self.request, upstream)
                return

            parsed = urllib.parse.urlsplit(target)
            if parsed.scheme != "http" or not parsed.hostname:
                raise ValueError("unsupported proxy request")
            host = parsed.hostname
            port = parsed.port or 80
            path = urllib.parse.urlunsplit(
                ("", "", parsed.path or "/", parsed.query, "")
            ).encode("ascii")
            forwarded = [method_bytes + b" " + path + b" " + version]
            forwarded.extend(
                line
                for line in lines[1:]
                if not line.lower().startswith((b"proxy-connection:", b"connection:"))
            )
            forwarded.append(b"Connection: close")
            upstream = _connect_public_host(host, port)
            with upstream:
                upstream.sendall(b"\r\n".join(forwarded) + b"\r\n\r\n" + remainder)
                _relay_sockets(self.request, upstream)
        except (OSError, ValueError, UnicodeError, json.JSONDecodeError):
            try:
                self.request.sendall(b"HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n")
            except OSError:
                pass


class _PinnedProxyServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class _PinnedPublicProxy:
    """Temporary local proxy that binds browser requests to public DoH IPs."""

    def __init__(self) -> None:
        self._server = _PinnedProxyServer(("127.0.0.1", 0), _PinnedProxyHandler)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="factreach-pinned-proxy",
            daemon=True,
        )

    @property
    def url(self) -> str:
        port = self._server.server_address[1]
        return f"http://127.0.0.1:{port}"

    def __enter__(self) -> _PinnedPublicProxy:
        self._thread.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)


def browser_harness_status(timeout: int = 10) -> BrowserHarnessStatus:
    """Probe the executable only; do not attach to Chrome from Doctor."""
    probe = probe_command(
        "browser-harness",
        ["--version"],
        timeout=timeout,
        package=BROWSER_HARNESS_PACKAGE,
    )
    if probe.status == "missing":
        return BrowserHarnessStatus(
            "off",
            False,
            "未安装 browser-harness；安装：uv tool install "
            + BROWSER_HARNESS_PACKAGE,
        )
    if not probe.ok:
        return BrowserHarnessStatus("error", True, probe.hint or probe.output)
    return BrowserHarnessStatus(
        "warn",
        True,
        "browser-harness 已安装；真实 Chrome 只在显式选择后连接，"
        "Doctor 不读取标签页或登录态",
    )


def _browser_script(target: str, proxy_url: str) -> str:
    target_literal = json.dumps(target, ensure_ascii=False)
    js_code = f"""
(() => {{
  const root = document.querySelector('main, article, [role="main"]');
  const selectedText = (root?.innerText || '').trim();
  const bodyText = (document.body?.innerText || '').trim();
  return {{
    url: location.href,
    title: document.title,
    ready: document.readyState,
    text: (selectedText || bodyText).slice(0, {_MAX_TEXT_CHARS})
  }};
}})()
""".strip()
    js_literal = json.dumps(js_code, ensure_ascii=False)
    return "\n".join(
        (
            "import base64",
            "import json",
            "import time",
            f"target = {target_literal}",
            f"proxy_url = {json.dumps(proxy_url)}",
            "def evaluate(expression):",
            "    response = cdp('Runtime.evaluate', session_id=sid, expression=expression, returnByValue=True, awaitPromise=True)",
            "    details = response.get('exceptionDetails')",
            "    remote = response.get('result') or {}",
            "    if details or remote.get('subtype') == 'error':",
            "        raise RuntimeError('browser JavaScript evaluation failed')",
            "    return remote.get('value')",
            "tab_id = None",
            "sid = None",
            "context_id = None",
            "payload = None",
            "load_seen = False",
            "blocked_url = None",
            "guarded_sessions = set()",
            "def guard_session(session_id):",
            "    cdp('Fetch.enable', session_id=session_id, patterns=[{'urlPattern': '*', 'requestStage': 'Request'}])",
            "    cdp('Target.setAutoAttach', session_id=session_id, autoAttach=True, waitForDebuggerOnStart=True, flatten=True)",
            "    guarded_sessions.add(session_id)",
            "try:",
            "    context_id = cdp('Target.createBrowserContext', proxyServer=proxy_url, proxyBypassList='<-loopback>')['browserContextId']",
            "    try:",
            "        source_cookies = cdp('Storage.getCookies').get('cookies') or []",
            "        cookie_keys = {'name', 'value', 'url', 'domain', 'path', 'secure', 'httpOnly', 'sameSite', 'expires', 'priority', 'sameParty', 'sourceScheme', 'sourcePort', 'partitionKey'}",
            "        copied_cookies = [{key: value for key, value in cookie.items() if key in cookie_keys} for cookie in source_cookies]",
            "        for offset in range(0, len(copied_cookies), 200):",
            "            batch = copied_cookies[offset:offset + 200]",
            "            try:",
            "                cdp('Storage.setCookies', cookies=batch, browserContextId=context_id)",
            "            except Exception:",
            "                for cookie in batch:",
            "                    try:",
            "                        cdp('Storage.setCookies', cookies=[cookie], browserContextId=context_id)",
            "                    except Exception:",
            "                        pass",
            "    except Exception:",
            "        pass",
            "    tab_id = cdp('Target.createTarget', url='about:blank', browserContextId=context_id)['targetId']",
            "    sid = cdp('Target.attachToTarget', targetId=tab_id, flatten=True)['sessionId']",
            "    cdp('Page.enable', session_id=sid)",
            "    cdp('Runtime.enable', session_id=sid)",
            "    cdp('Network.enable', session_id=sid)",
            "    guard_session(sid)",
            "    drain_events()",
            f"    evaluate('location.assign(' + {json.dumps(target_literal)} + ')')",
            "    deadline = time.time() + 30",
            "    last_text = None",
            "    stable_samples = 0",
            "    first_text_at = None",
            "    while time.time() < deadline:",
            "        for event in drain_events():",
            "            event_session = event.get('session_id')",
            "            if event.get('method') == 'Target.attachedToTarget':",
            "                params = event.get('params') or {}",
            "                child_sid = params.get('sessionId')",
            "                if child_sid:",
            "                    try:",
            "                        guard_session(child_sid)",
            "                        cdp('Runtime.runIfWaitingForDebugger', session_id=child_sid)",
            "                    except Exception:",
            "                        blocked_url = 'descendant target could not be guarded'",
            "                continue",
            "            if event.get('method') != 'Fetch.requestPaused':",
            "                continue",
            "            params = event.get('params') or {}",
            "            request = params.get('request') or {}",
            "            request_id = params.get('requestId')",
            "            request_url = request.get('url', '')",
            "            if request_id and event_session in guarded_sessions:",
            "                cdp('Fetch.continueRequest', session_id=event_session, requestId=request_id)",
            "            elif request_id:",
            "                blocked_url = request_url or 'unguarded browser request'",
            "        if blocked_url:",
            "            raise RuntimeError(f'browser navigation blocked a non-public request: {blocked_url[:200]}')",
            "        try:",
            f"            current = evaluate({js_literal})",
            "        except Exception:",
            "            current = None",
            "        if isinstance(current, dict) and current.get('ready') == 'complete':",
            "            load_seen = True",
            "            text_value = (current.get('text') or '').strip()",
            "            if text_value:",
            "                if first_text_at is None:",
            "                    first_text_at = time.time()",
            "                if text_value == last_text:",
            "                    stable_samples += 1",
            "                else:",
            "                    last_text = text_value",
            "                    stable_samples = 0",
            "                payload = current",
            "                if stable_samples >= 2 and time.time() - first_text_at >= 1.5:",
            "                    break",
            "        wait(0.25)",
            "    if not load_seen:",
            "        raise TimeoutError('browser page did not finish loading')",
            "    if not isinstance(payload, dict) or not (payload.get('text') or '').strip():",
            "        raise RuntimeError('browser page contained no visible text after rendering')",
            "finally:",
            "    if context_id is not None:",
            "        try:",
            "            cdp('Target.disposeBrowserContext', browserContextId=context_id)",
            "        except Exception:",
            "            pass",
            "encoded = base64.b64encode(",
            "    json.dumps(payload, ensure_ascii=False).encode('utf-8')",
            ").decode('ascii')",
            f"print('{_RESULT_PREFIX}' + encoded)",
        )
    )


def _stop_isolated_daemon(env: dict[str, str]) -> None:
    """Best-effort cleanup for the per-read browser-harness daemon."""
    try:
        subprocess.run(
            ["browser-harness", "--reload"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            shell=False,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass


def browser_harness_read(url: str, *, timeout: int = 90) -> str:
    """Open one public URL in the user's Chrome and return visible page text.

    This function must only be called after explicit user/CLI authorization.
    It deliberately passes code on stdin and never invokes a shell.
    """
    target = normalize_public_http_url(url)
    child_env = utf8_subprocess_env()
    child_env["BU_NAME"] = (
        f"factreach-{os.getpid()}-{secrets.token_hex(6)}"
    )
    try:
        try:
            with _PinnedPublicProxy() as proxy:
                result = subprocess.run(
                    ["browser-harness"],
                    input=_browser_script(target, proxy.url),
                    capture_output=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=timeout,
                    shell=False,
                    env=child_env,
                )
        finally:
            _stop_isolated_daemon(child_env)
    except FileNotFoundError as exc:
        raise BrowserHarnessError(
            "browser-harness is not installed; run: uv tool install "
            + BROWSER_HARNESS_PACKAGE
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise BrowserHarnessError(
            f"browser-harness timed out after {timeout}s"
        ) from exc
    except OSError as exc:
        raise BrowserHarnessError(f"browser-harness could not start: {exc}") from exc

    if result.returncode != 0:
        diagnostic = (result.stderr or result.stdout or "unknown error").strip()
        detail = next(
            (line.strip() for line in reversed(diagnostic.splitlines()) if line.strip()),
            "unknown error",
        )[:500]
        raise BrowserHarnessError(detail)
    marker_line = next(
        (
            line
            for line in result.stdout.splitlines()
            if line.startswith(_RESULT_PREFIX)
        ),
        None,
    )
    if marker_line is None:
        raise BrowserHarnessError("browser-harness returned no readable page result")
    encoded = marker_line[len(_RESULT_PREFIX) :]
    try:
        payload = json.loads(base64.b64decode(encoded).decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BrowserHarnessError("browser-harness returned an invalid result") from exc
    final_url = payload.get("url") if isinstance(payload, dict) else None
    if not isinstance(final_url, str):
        raise BrowserHarnessError("browser-harness returned no final page URL")
    try:
        normalize_public_http_url(final_url)
    except ValueError as exc:
        raise BrowserHarnessError(
            "browser-harness redirected to a non-public destination; content was blocked"
        ) from exc
    text = payload.get("text") if isinstance(payload, dict) else None
    if not isinstance(text, str) or not text.strip():
        raise BrowserHarnessError("browser-harness page contained no visible text")
    return text
