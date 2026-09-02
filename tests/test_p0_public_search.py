# -*- coding: utf-8 -*-
"""P0 zero-auth search and public-source channel contracts."""

import json
import subprocess
from pathlib import Path

from agent_reach import cli
from agent_reach.backends.opencli import (
    PUBLIC_OPENCLI_ADAPTERS,
    WECHAT_OPENCLI_ADAPTERS,
    probe_opencli_public_adapters,
    probe_opencli_wechat_adapter,
    probe_opencli_weibo_adapter,
)
from agent_reach.channels.academic import AcademicChannel
from agent_reach.channels.github_trending import GitHubTrendingChannel
from agent_reach.channels.hackernews import HackerNewsChannel
from agent_reach.channels.stackoverflow import StackOverflowChannel
from agent_reach.channels.web_search import WebSearchChannel
from agent_reach.channels.wechat_public import WeChatPublicChannel
from agent_reach.probe import ProbeResult


def _search_result(engine: str, *, total: int = 1, failures=None):
    return {
        "status": "ok",
        "data": {
            "query": "OpenAI",
            "engines": [engine],
            "totalResults": total,
            "results": ([{"title": "OpenAI", "url": "https://openai.com"}]
                        if total else []),
            "partialFailures": failures or [],
        },
        "error": None,
        "hint": None,
    }


def test_web_search_prefers_duckduckgo_and_parses_structured_success(monkeypatch):
    calls = []
    monkeypatch.setenv("DEFAULT_SEARCH_ENGINE", "bing")
    monkeypatch.setenv("ALLOWED_SEARCH_ENGINES", "duckduckgo")
    monkeypatch.setattr("shutil.which", lambda name: "/bin/open-websearch")

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        payload = _search_result("duckduckgo")
        return subprocess.CompletedProcess(argv, 0, json.dumps(payload), "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    channel = WebSearchChannel()
    status, message = channel.check()

    assert status == "ok"
    assert channel.active_backend == "open-websearch:duckduckgo"
    assert "DuckDuckGo" in message
    assert calls[0][0][1:] == [
        "search", "OpenAI", "--limit", "1", "--engine", "duckduckgo", "--json"
    ]
    assert calls[0][1]["env"]["DEFAULT_SEARCH_ENGINE"] == "bing"
    assert calls[0][1]["env"]["ALLOWED_SEARCH_ENGINES"] == "duckduckgo"


def test_web_search_falls_back_when_exit_zero_contains_no_results(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/bin/open-websearch")

    def fake_run(argv, **kwargs):
        engine = argv[argv.index("--engine") + 1]
        if engine == "duckduckgo":
            payload = _search_result(
                engine,
                total=0,
                failures=[{"engine": engine, "error": "upstream blocked"}],
            )
        else:
            payload = _search_result(engine)
        return subprocess.CompletedProcess(argv, 0, json.dumps(payload), "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    channel = WebSearchChannel()
    status, message = channel.check()

    assert status == "ok"
    assert channel.active_backend == "open-websearch:brave"


def test_web_search_rejects_result_from_wrong_engine(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/bin/open-websearch")
    outcomes = iter(
        [
            _search_result("bing"),
            _search_result("brave"),
        ]
    )

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, json.dumps(next(outcomes)), ""
        ),
    )

    channel = WebSearchChannel()
    status, message = channel.check()

    assert status == "ok"
    assert channel.active_backend == "open-websearch:brave"
    assert "DuckDuckGo" in message
    assert "Brave" in message


def test_web_search_missing_has_explicit_install_guide(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _name: None)

    channel = WebSearchChannel()
    status, message = channel.check()

    assert status == "off"
    assert channel.active_backend is None
    assert "npm install -g open-websearch" in message


def test_web_search_reports_broken_shim_instead_of_network_failure(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/bin/open-websearch")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda argv, **kwargs: subprocess.CompletedProcess(argv, 127, "", "missing node"),
    )

    channel = WebSearchChannel()
    status, message = channel.check()

    assert status == "error"
    assert channel.active_backend is None
    assert "无法执行" in message
    assert "重装" in message


def test_web_search_reports_incompatible_cli_instead_of_network_failure(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/bin/open-websearch")

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda argv, **kwargs: subprocess.CompletedProcess(
            argv, 2, "", "unknown option --engine"
        ),
    )

    channel = WebSearchChannel()
    status, message = channel.check()

    assert status == "error"
    assert "版本不兼容" in message
    assert "升级" in message


def test_public_opencli_channels_are_zero_auth_and_report_runtime_only(
    monkeypatch,
):
    monkeypatch.setattr(
        "agent_reach.channels._opencli_public.probe_opencli_adapters",
        lambda adapters: ProbeResult("ok", output=",".join(adapters)),
    )

    channels = [
        HackerNewsChannel(),
        AcademicChannel(),
        StackOverflowChannel(),
        GitHubTrendingChannel(),
    ]
    for channel in channels:
        status, message = channel.check()
        assert channel.tier == 0
        assert status == "warn"
        assert channel.active_backend is None
        assert "无需 Cookie / Chrome 扩展" in message
        assert "非空 JSON" in message


def test_wechat_public_needs_bridge_but_not_platform_cookie(monkeypatch):
    from agent_reach.backends import OpenCLIStatus

    monkeypatch.setattr(
        "agent_reach.backends.opencli_status",
        lambda: OpenCLIStatus(
            installed=True,
            extension_connected=True,
            version="1.8.6",
        ),
    )
    monkeypatch.setattr(
        "agent_reach.backends.probe_opencli_wechat_adapter",
        lambda: ProbeResult("ok", output="weixin"),
    )

    channel = WeChatPublicChannel()
    status, message = channel.check()

    assert channel.tier == 1
    assert status == "warn"
    assert channel.active_backend is None
    assert "不需公众号 Cookie" in message
    assert "Browser Bridge" in message


def test_public_opencli_channels_cover_expected_urls():
    assert HackerNewsChannel().can_handle("https://news.ycombinator.com/item?id=1")
    assert WeChatPublicChannel().can_handle("https://mp.weixin.qq.com/s/abc")
    assert AcademicChannel().can_handle("https://arxiv.org/abs/2501.00001")
    assert AcademicChannel().can_handle(
        "https://pubmed.ncbi.nlm.nih.gov/12345678/"
    )
    assert AcademicChannel().can_handle("https://openreview.net/forum?id=abc")
    assert StackOverflowChannel().can_handle(
        "https://stackoverflow.com/questions/1/example"
    )
    assert GitHubTrendingChannel().can_handle("https://github.com/trending/python")
    assert not GitHubTrendingChannel().can_handle(
        "https://github.com/acme/trending-widget"
    )
    assert not GitHubTrendingChannel().can_handle(
        "https://github.com/acme/repo?q=/trending"
    )


def test_github_trending_routes_before_generic_github():
    from agent_reach.channels import get_all_channels

    url = "https://github.com/trending/python"
    matches = [channel.name for channel in get_all_channels() if channel.can_handle(url)]

    assert matches[:2] == ["github_trending", "github"]


def _write_opencli_manifest(tmp_path: Path, entries: list[dict]) -> Path:
    manifest = tmp_path / "cli-manifest.json"
    manifest.write_text(json.dumps(entries), encoding="utf-8")
    return manifest


def test_opencli_public_adapter_probe_uses_structured_manifest(monkeypatch, tmp_path):
    assert "weixin" not in PUBLIC_OPENCLI_ADAPTERS
    entries = [{"site": adapter} for adapter in PUBLIC_OPENCLI_ADAPTERS]
    manifest = _write_opencli_manifest(tmp_path, entries)

    def fake_probe(command, args, **kwargs):
        assert (command, args) == ("opencli", ["--version"])
        return ProbeResult("ok", output="1.8.7")

    monkeypatch.setattr("agent_reach.backends.opencli.probe_command", fake_probe)
    monkeypatch.setattr(
        "agent_reach.backends.opencli._opencli_manifest_path", lambda: manifest
    )

    result = probe_opencli_public_adapters()

    assert result.ok
    assert result.output == "1.8.7"


def test_opencli_weibo_probe_requires_adapter_in_manifest(monkeypatch, tmp_path):
    manifest = _write_opencli_manifest(tmp_path, [{"site": "weibo"}])

    def fake_probe(command, args, **kwargs):
        assert (command, args) == ("opencli", ["--version"])
        return ProbeResult("ok", output="1.8.7")

    monkeypatch.setattr("agent_reach.backends.opencli.probe_command", fake_probe)
    monkeypatch.setattr(
        "agent_reach.backends.opencli._opencli_manifest_path", lambda: manifest
    )

    assert probe_opencli_weibo_adapter().ok


def test_opencli_wechat_probe_requires_weixin_adapter(monkeypatch, tmp_path):
    manifest = _write_opencli_manifest(
        tmp_path, [{"site": WECHAT_OPENCLI_ADAPTERS[0]}]
    )

    def fake_probe(command, args, **kwargs):
        assert (command, args) == ("opencli", ["--version"])
        return ProbeResult("ok", output="1.8.7")

    monkeypatch.setattr("agent_reach.backends.opencli.probe_command", fake_probe)
    monkeypatch.setattr(
        "agent_reach.backends.opencli._opencli_manifest_path", lambda: manifest
    )

    assert probe_opencli_wechat_adapter().ok


def test_opencli_weibo_probe_rejects_old_manifest(monkeypatch, tmp_path):
    manifest = _write_opencli_manifest(tmp_path, [{"site": "facebook"}])

    def fake_probe(command, args, **kwargs):
        assert (command, args) == ("opencli", ["--version"])
        return ProbeResult("ok", output="old")

    monkeypatch.setattr("agent_reach.backends.opencli.probe_command", fake_probe)
    monkeypatch.setattr(
        "agent_reach.backends.opencli._opencli_manifest_path", lambda: manifest
    )

    result = probe_opencli_weibo_adapter()
    assert not result.ok
    assert "weibo" in result.hint


def test_opencli_public_adapter_probe_rejects_missing_manifest_site(
    monkeypatch, tmp_path
):
    entries = [
        {"site": adapter}
        for adapter in PUBLIC_OPENCLI_ADAPTERS
        if adapter != "github-trending"
    ]

    manifest = _write_opencli_manifest(tmp_path, entries)

    def fake_probe(command, args, **kwargs):
        assert (command, args) == ("opencli", ["--version"])
        return ProbeResult("ok", output="old")

    monkeypatch.setattr("agent_reach.backends.opencli.probe_command", fake_probe)
    monkeypatch.setattr(
        "agent_reach.backends.opencli._opencli_manifest_path", lambda: manifest
    )

    result = probe_opencli_public_adapters()

    assert not result.ok
    assert "github-trending" in result.hint


def test_opencli_public_adapter_probe_reads_manifest_without_cli_list(
    monkeypatch, tmp_path
):
    entries = [{"site": adapter} for adapter in PUBLIC_OPENCLI_ADAPTERS]
    manifest = _write_opencli_manifest(tmp_path, entries)

    def fake_probe(command, args, **kwargs):
        assert (command, args) == ("opencli", ["--version"])
        return ProbeResult("ok", output="1.8.7", stdout="1.8.7")

    monkeypatch.setattr("agent_reach.backends.opencli.probe_command", fake_probe)
    monkeypatch.setattr(
        "agent_reach.backends.opencli._opencli_manifest_path", lambda: manifest
    )

    assert probe_opencli_public_adapters().ok


def test_opencli_adapter_probe_rejects_missing_static_manifest(monkeypatch):
    monkeypatch.setattr(
        "agent_reach.backends.opencli.probe_command",
        lambda *args, **kwargs: ProbeResult("ok", output="1.8.7"),
    )
    monkeypatch.setattr(
        "agent_reach.backends.opencli._opencli_manifest_path", lambda: None
    )

    result = probe_opencli_public_adapters()

    assert not result.ok
    assert "cli-manifest.json" in result.hint


def test_public_opencli_channel_missing_is_not_misreported_as_available(
    monkeypatch,
):
    monkeypatch.setattr(
        "agent_reach.channels._opencli_public.probe_opencli_adapters",
        lambda _adapters: ProbeResult("missing"),
    )

    channel = HackerNewsChannel()
    status, message = channel.check()

    assert status == "off"
    assert channel.active_backend is None
    assert "npm install -g @jackwener/opencli" in message


def test_public_opencli_channel_rejects_missing_required_adapter(monkeypatch):
    monkeypatch.setattr(
        "agent_reach.channels._opencli_public.probe_opencli_adapters",
        lambda adapters: ProbeResult(
            "error", hint=f"OpenCLI 缺少公开适配器：{adapters[0]}"
        ),
    )

    channel = HackerNewsChannel()
    status, message = channel.check()

    assert status == "error"
    assert channel.active_backend is None
    assert "hackernews" in message


def test_wechat_public_rejects_missing_weixin_adapter(monkeypatch):
    from agent_reach.backends import OpenCLIStatus

    monkeypatch.setattr(
        "agent_reach.backends.opencli_status",
        lambda: OpenCLIStatus(
            installed=True,
            extension_connected=True,
            version="1.8.6",
        ),
    )
    monkeypatch.setattr(
        "agent_reach.backends.probe_opencli_wechat_adapter",
        lambda: ProbeResult("error", hint="OpenCLI 缺少公开适配器：weixin"),
    )

    status, message = WeChatPublicChannel().check()

    assert status == "error"
    assert "weixin" in message


def test_open_websearch_installer_uses_official_global_package(monkeypatch):
    calls = []
    installed = {"value": False}

    def fake_which(name):
        if name == "npm":
            return "/usr/bin/npm"
        if name == "open-websearch" and installed["value"]:
            return "/usr/bin/open-websearch"
        return None

    def fake_run(argv, **kwargs):
        calls.append(argv)
        if argv[-2:] == ["search", "--help"]:
            return subprocess.CompletedProcess(
                argv,
                1,
                "",
                "Usage: open-websearch search <query> --engine --json",
            )
        installed["value"] = True
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr("shutil.which", fake_which)
    monkeypatch.setattr(subprocess, "run", fake_run)

    assert cli._install_open_websearch_deps() is True
    assert calls == [
        ["/usr/bin/npm", "install", "-g", "open-websearch"],
        ["/usr/bin/open-websearch", "search", "--help"],
    ]


def test_open_websearch_installer_replaces_incompatible_existing_cli(monkeypatch):
    calls = []

    monkeypatch.setattr(
        "shutil.which",
        lambda name: f"/usr/bin/{name}" if name in {"npm", "open-websearch"} else None,
    )

    def fake_run(argv, **kwargs):
        calls.append(argv)
        if argv[0].endswith("open-websearch") and len(calls) == 1:
            return subprocess.CompletedProcess(argv, 0, "old help", "")
        if argv[0].endswith("open-websearch"):
            return subprocess.CompletedProcess(
                argv,
                1,
                "",
                "Usage: open-websearch search <query> --engine --json",
            )
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert cli._install_open_websearch_deps() is True
    assert ["/usr/bin/npm", "install", "-g", "open-websearch"] in calls


def test_open_websearch_installer_rejects_plural_engine_only_cli(monkeypatch):
    calls = []
    installed = {"value": False}

    monkeypatch.setattr(
        "shutil.which",
        lambda name: f"/usr/bin/{name}"
        if name in {"npm", "open-websearch"}
        else None,
    )

    def fake_run(argv, **kwargs):
        calls.append(argv)
        if argv[0].endswith("npm"):
            installed["value"] = True
            return subprocess.CompletedProcess(argv, 0, "", "")
        if installed["value"]:
            help_text = "Usage: open-websearch search <query> --engine NAME --json"
        else:
            help_text = "Usage: open-websearch search <query> --engines a,b --json"
        return subprocess.CompletedProcess(argv, 1, help_text, "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert cli._install_open_websearch_deps() is True
    assert ["/usr/bin/npm", "install", "-g", "open-websearch"] in calls


def test_opencli_public_installer_upgrades_when_adapters_are_missing(monkeypatch):
    calls = []
    probes = iter(
        [
            ProbeResult("error", hint="missing hackernews"),
            ProbeResult("ok", output="2.1.0"),
        ]
    )
    monkeypatch.setattr(
        "agent_reach.backends.probe_opencli_public_adapters",
        lambda: next(probes),
    )
    monkeypatch.setattr(
        "shutil.which", lambda name: "/usr/bin/npm" if name == "npm" else None
    )

    def fake_run(argv, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert cli._install_opencli_public_deps() is True
    assert calls == [
        ["/usr/bin/npm", "install", "-g", "@jackwener/opencli"]
    ]


def test_weibo_installer_upgrades_when_adapter_is_missing(monkeypatch):
    calls = []
    probes = iter(
        [
            ProbeResult("error", hint="missing weibo"),
            ProbeResult("ok", output="2.1.0"),
        ]
    )
    monkeypatch.setattr(
        "agent_reach.backends.probe_opencli_weibo_adapter",
        lambda: next(probes),
    )
    monkeypatch.setattr(
        "shutil.which", lambda name: "/usr/bin/npm" if name == "npm" else None
    )
    monkeypatch.setattr(
        cli, "_install_opencli_deps", lambda: calls.append("runtime") or True
    )

    def fake_run(argv, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert cli._install_weibo_deps() is True
    assert calls == [
        ["/usr/bin/npm", "install", "-g", "@jackwener/opencli"],
        "runtime",
    ]


def test_public_sources_channel_aliases_share_one_opencli_installer(
    monkeypatch, capsys
):
    calls = []
    monkeypatch.setattr(cli, "_install_system_deps", lambda: True)
    monkeypatch.setattr(cli, "_install_mcporter", lambda: True)
    monkeypatch.setattr(
        cli, "_install_opencli_public_deps", lambda: calls.append("opencli") or True
    )
    monkeypatch.setattr(
        cli, "_install_wechat_deps", lambda: calls.append("wechat") or True
    )
    monkeypatch.setattr(
        cli, "_install_open_websearch_deps", lambda: calls.append("web") or True
    )
    monkeypatch.setattr(cli, "_install_skill", lambda: True)
    monkeypatch.setattr(
        "agent_reach.doctor.check_all",
        lambda config: {},
    )
    monkeypatch.setattr("agent_reach.doctor.format_report", lambda results: "report")

    from argparse import Namespace

    cli._cmd_install(
        Namespace(
            env="local",
            proxy="",
            system=True,
            safe=False,
            dry_run=False,
            channels=(
                "open-websearch,hackernews,wechat,academic,stackoverflow,"
                "github-trending"
            ),
        )
    )

    assert calls.count("web") == 1
    assert calls.count("opencli") == 1
    assert calls.count("wechat") == 1
    assert "Installation complete" in capsys.readouterr().out


def test_wechat_installer_validates_adapter_before_browser_setup(monkeypatch):
    calls = []
    monkeypatch.setattr(
        cli,
        "_install_opencli_wechat_deps",
        lambda: calls.append("manifest") or True,
    )
    monkeypatch.setattr(
        cli,
        "_install_opencli_deps",
        lambda: calls.append("bridge") or True,
    )

    assert cli._install_wechat_deps() is True
    assert calls == ["manifest", "bridge"]


def test_wechat_installer_stops_when_adapter_is_missing(monkeypatch):
    calls = []
    monkeypatch.setattr(
        cli,
        "_install_opencli_wechat_deps",
        lambda: calls.append("manifest") or False,
    )
    monkeypatch.setattr(
        cli,
        "_install_opencli_deps",
        lambda: calls.append("bridge") or True,
    )

    assert cli._install_wechat_deps() is False
    assert calls == ["manifest"]
