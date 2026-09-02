# -*- coding: utf-8 -*-
"""Zero-auth web search with real per-engine fallback probing."""

from __future__ import annotations

import json
import re
import shutil
import subprocess

from agent_reach.utils.process import utf8_subprocess_env

from .base import Channel

_ENGINE_LABELS = {
    "duckduckgo": "DuckDuckGo",
    "brave": "Brave",
    "bing": "Bing",
}
_PROBE_QUERY = "OpenAI"


def open_websearch_runtime_ready(executable: str, timeout: int = 20) -> bool:
    """Check the CLI surface FactReach requires without issuing a search."""
    try:
        result = subprocess.run(
            [executable, "search", "--help"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    output = (result.stdout or "") + (result.stderr or "")
    return (
        result.returncode in {0, 1}
        and "Usage: open-websearch search" in output
        and re.search(r"(?<![-\w])--engine(?=$|[\s,=\]])", output) is not None
        and re.search(r"(?<![-\w])--json(?=$|[\s,=\]])", output) is not None
    )


class WebSearchChannel(Channel):
    name = "web_search"
    description = "全网关键词搜索"
    backends = [
        "open-websearch:duckduckgo",
        "open-websearch:brave",
        "open-websearch:bing",
    ]
    tier = 0

    def can_handle(self, url: str) -> bool:
        return False

    def check(self, config=None):
        self.active_backend = None
        executable = shutil.which("open-websearch")
        if not executable:
            return "off", (
                "open-websearch 未安装。安装：\n"
                "  npm install -g open-websearch"
            )

        failures: list[str] = []
        for backend in self.ordered_backends(config):
            engine = backend.split(":", 1)[1]
            outcome = _probe_search_engine(executable, engine)
            if outcome == "ok":
                self.active_backend = backend
                label = _ENGINE_LABELS[engine]
                if failures:
                    failed_labels = "、".join(
                        _ENGINE_LABELS[item] for item in failures
                    )
                    return "ok", (
                        f"{failed_labels} 实搜失败，已自动切换到 {label}；"
                        "无需 API Key"
                    )
                return "ok", f"{label} 实搜成功；无需 API Key"
            if outcome == "broken":
                return "error", (
                    "open-websearch 命令无法执行或版本不兼容。重装/升级：\n"
                    "  npm install -g open-websearch"
                )
            failures.append(engine)

        labels = "、".join(_ENGINE_LABELS[item] for item in failures)
        return "warn", (
            f"open-websearch 可执行，但 {labels} 实搜均未返回有效结果；"
            "请检查当前网络后重试"
        )


def _probe_search_engine(executable: str, engine: str, timeout: int = 20) -> str:
    env = utf8_subprocess_env()
    argv = [
        executable,
        "search",
        _PROBE_QUERY,
        "--limit",
        "1",
        "--engine",
        engine,
        "--json",
    ]
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
        )
    except (FileNotFoundError, OSError):
        return "broken"
    except subprocess.TimeoutExpired:
        return "failed"
    if result.returncode in {126, 127}:
        return "broken"
    if result.returncode != 0:
        error_text = f"{result.stdout}\n{result.stderr}".casefold()
        incompatible_markers = (
            "unknown option",
            "unrecognized argument",
            "unrecognized option",
            "no such option",
            "invalid option",
        )
        if "--engine" in error_text and any(
            marker in error_text for marker in incompatible_markers
        ):
            return "broken"
        return "failed"
    try:
        payload = json.loads(result.stdout)
    except (TypeError, json.JSONDecodeError):
        return "failed"
    if not isinstance(payload, dict) or payload.get("status") != "ok":
        return "failed"
    data = payload.get("data")
    if not isinstance(data, dict):
        return "failed"
    reported_engines = data.get("engines")
    if not isinstance(reported_engines, list) or engine not in reported_engines:
        return "failed"
    results = data.get("results")
    if not isinstance(results, list) or not results:
        return "failed"
    return "ok"
