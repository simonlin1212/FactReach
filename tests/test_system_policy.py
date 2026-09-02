"""Tests for the opt-in CLAUDE.md / AGENTS.md evidence policy."""

from __future__ import annotations

import os
import stat
from unittest.mock import patch

import pytest

from agent_reach import system_policy
from agent_reach.cli import main
from agent_reach.system_policy import (
    POLICY_END,
    POLICY_START,
    SystemPolicyError,
    install_policy,
    load_policy,
    policy_status,
    remove_policy,
    resolve_targets,
)


def test_policy_templates_are_managed_system_instructions():
    zh = load_policy("zh")
    en = load_policy("en")

    for text in (zh, en):
        assert text.startswith(POLICY_START)
        assert text.rstrip().endswith(POLICY_END)
        assert "factreach doctor --json" in text
    assert "不得只凭模型记忆" in zh
    assert "两个相互独立的来源" in zh
    assert "Do not rely on model memory alone" in en
    assert "two independent sources" in en


def test_resolve_project_targets(tmp_path):
    targets = resolve_targets("both", "project", cwd=tmp_path)

    assert targets == {
        "claude": tmp_path / "CLAUDE.md",
        "codex": tmp_path / "AGENTS.md",
    }


def test_resolve_project_codex_target_prefers_override(tmp_path):
    override = tmp_path / "AGENTS.override.md"
    override.write_text("# Active Codex rules\n", encoding="utf-8")

    targets = resolve_targets("codex", "project", cwd=tmp_path)

    assert targets == {"codex": override}


def test_resolve_auto_targets_detects_existing_agent(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("# Claude\n", encoding="utf-8")

    targets = resolve_targets("auto", "project", cwd=tmp_path)

    assert targets == {"claude": tmp_path / "CLAUDE.md"}


def test_resolve_user_targets_honors_config_roots(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "claude-home"))
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex-home"))

    targets = resolve_targets("both", "user", home=tmp_path)

    assert targets["claude"] == tmp_path / "claude-home" / "CLAUDE.md"
    assert targets["codex"] == tmp_path / "codex-home" / "AGENTS.md"


def test_resolve_user_targets_ignore_empty_config_roots(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", "")
    monkeypatch.setenv("CODEX_HOME", "")

    targets = resolve_targets("both", "user", home=tmp_path)

    assert targets["claude"] == tmp_path / ".claude" / "CLAUDE.md"
    assert targets["codex"] == tmp_path / ".codex" / "AGENTS.md"


def test_resolve_user_targets_reject_relative_config_roots(monkeypatch, tmp_path):
    monkeypatch.setenv("CODEX_HOME", "relative-codex-home")

    with pytest.raises(SystemPolicyError, match="absolute path"):
        resolve_targets("codex", "user", home=tmp_path)


def test_install_policy_preserves_content_and_is_idempotent(tmp_path):
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# Existing rules\n\nKeep this.\n", encoding="utf-8")
    agents.chmod(0o640)

    assert install_policy(agents, language="zh") == "updated"
    first = agents.read_text(encoding="utf-8")
    assert first.startswith("# Existing rules\n\nKeep this.\n")
    assert first.count(POLICY_START) == 1
    assert first.count(POLICY_END) == 1
    if os.name != "nt":
        # Windows exposes synthetic POSIX mode bits; chmod preservation is a
        # Unix contract and file ACLs remain under Windows' native control.
        assert stat.S_IMODE(agents.stat().st_mode) == 0o640
    assert policy_status(agents) == "installed"

    assert install_policy(agents, language="zh") == "unchanged"
    assert agents.read_text(encoding="utf-8") == first


def test_install_policy_replaces_only_managed_block(tmp_path):
    agents = tmp_path / "AGENTS.md"
    agents.write_text(
        f"before\n\n{POLICY_START}\nold rule\n{POLICY_END}\n\nafter\n",
        encoding="utf-8",
    )

    assert install_policy(agents, language="en") == "updated"
    updated = agents.read_text(encoding="utf-8")
    assert updated.startswith("before\n\n")
    assert updated.endswith("\n\nafter\n")
    assert "old rule" not in updated
    assert "Do not rely on model memory alone" in updated


def test_policy_status_detects_outdated_managed_block(tmp_path):
    agents = tmp_path / "AGENTS.md"
    agents.write_text(
        f"{POLICY_START}\nold rule\n{POLICY_END}\n",
        encoding="utf-8",
    )

    assert policy_status(agents) == "outdated"
    assert install_policy(agents, language="zh") == "updated"
    assert policy_status(agents) == "installed"


def test_remove_policy_preserves_other_instructions(tmp_path):
    agents = tmp_path / "AGENTS.md"
    agents.write_text(
        f"# Before\n\n{load_policy('zh')}\n# After\n",
        encoding="utf-8",
    )

    installed = agents.read_text(encoding="utf-8")
    start = installed.index(POLICY_START)
    end = installed.index(POLICY_END, start) + len(POLICY_END)
    expected = installed[:start] + installed[end:]

    assert remove_policy(agents) == "removed"
    assert agents.read_text(encoding="utf-8") == expected
    assert remove_policy(agents) == "unchanged"


def test_remove_policy_preserves_significant_surrounding_whitespace(tmp_path):
    agents = tmp_path / "AGENTS.md"
    agents.write_text(
        f"hard break  \n\n{load_policy('zh')}    indented rule\n",
        encoding="utf-8",
    )
    before = agents.read_text(encoding="utf-8")
    start = before.index(POLICY_START)
    end = before.index(POLICY_END, start) + len(POLICY_END)

    assert remove_policy(agents) == "removed"
    assert agents.read_text(encoding="utf-8") == before[:start] + before[end:]


def test_install_policy_rejects_result_over_size_limit(
    tmp_path, monkeypatch
):
    agents = tmp_path / "AGENTS.md"
    agents.write_text("x" * 80, encoding="utf-8")
    monkeypatch.setattr(system_policy, "MAX_INSTRUCTION_BYTES", 100)

    with pytest.raises(SystemPolicyError, match="would exceed"):
        install_policy(agents)

    assert agents.read_text(encoding="utf-8") == "x" * 80


def test_install_policy_refuses_symlink(tmp_path):
    victim = tmp_path / "victim.md"
    victim.write_text("do not touch\n", encoding="utf-8")
    target = tmp_path / "AGENTS.md"
    try:
        target.symlink_to(victim)
    except OSError:
        pytest.skip("symlinks are not supported")

    with pytest.raises(SystemPolicyError, match="symlink"):
        install_policy(target)

    assert victim.read_text(encoding="utf-8") == "do not touch\n"


def test_broken_policy_markers_fail_closed(tmp_path):
    agents = tmp_path / "AGENTS.md"
    agents.write_text(f"{POLICY_START}\nincomplete\n", encoding="utf-8")

    assert policy_status(agents) == "broken"
    with pytest.raises(SystemPolicyError, match="incomplete or duplicate"):
        install_policy(agents)


def test_reversed_policy_markers_fail_closed(tmp_path):
    agents = tmp_path / "AGENTS.md"
    agents.write_text(
        f"{POLICY_END}\nconflict\n{POLICY_START}\n",
        encoding="utf-8",
    )

    assert policy_status(agents) == "broken"
    with pytest.raises(SystemPolicyError, match="reversed"):
        install_policy(agents)


def test_policy_show_is_read_only(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    with patch("sys.argv", ["factreach", "policy", "--show"]):
        main()

    output = capsys.readouterr().out
    assert "CLAUDE.md" in output
    assert "AGENTS.md" in output
    assert POLICY_START in output
    assert not (tmp_path / "CLAUDE.md").exists()
    assert not (tmp_path / "AGENTS.md").exists()


def test_policy_install_requires_explicit_target(capsys):
    with patch("sys.argv", ["factreach", "policy", "--install"]):
        with pytest.raises(SystemExit) as exc:
            main()

    assert exc.value.code == 2
    assert "requires --target" in capsys.readouterr().err


def test_policy_cli_installs_and_checks_project_files(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    with patch(
        "sys.argv",
        [
            "factreach",
            "policy",
            "--install",
            "--target",
            "both",
            "--scope",
            "project",
        ],
    ):
        main()

    assert policy_status(tmp_path / "CLAUDE.md") == "installed"
    assert policy_status(tmp_path / "AGENTS.md") == "installed"
    assert "created" in capsys.readouterr().out

    with patch(
        "sys.argv",
        [
            "factreach",
            "policy",
            "--check",
            "--target",
            "both",
            "--scope",
            "project",
        ],
    ):
        main()

    output = capsys.readouterr().out
    assert "claude: installed" in output
    assert "codex: installed" in output

    with patch(
        "sys.argv",
        [
            "factreach",
            "policy",
            "--uninstall",
            "--target",
            "both",
            "--scope",
            "project",
        ],
    ):
        main()

    assert policy_status(tmp_path / "CLAUDE.md") == "missing"
    assert policy_status(tmp_path / "AGENTS.md") == "missing"
    assert "removed" in capsys.readouterr().out


def test_policy_auto_language_uses_english_locale(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGENT_REACH_LANG", "en")

    with patch("sys.argv", ["factreach", "policy", "--show"]):
        main()

    output = capsys.readouterr().out
    assert "Do not rely on model memory alone" in output
    assert "不得只凭模型记忆" not in output


def test_policy_auto_language_defaults_unknown_locale_to_english(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AGENT_REACH_LANG", raising=False)
    monkeypatch.setenv("LC_ALL", "fr_FR.UTF-8")
    monkeypatch.setenv("LANG", "zh_CN.UTF-8")

    with patch("sys.argv", ["factreach", "policy", "--show"]):
        main()

    output = capsys.readouterr().out
    assert "Do not rely on model memory alone" in output
    assert "不得只凭模型记忆" not in output


def test_policy_explicit_language_override_wins_over_locale(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGENT_REACH_LANG", "zh")
    monkeypatch.setenv("LC_ALL", "en_US.UTF-8")
    monkeypatch.setenv("LANG", "en_US.UTF-8")

    with patch("sys.argv", ["factreach", "policy", "--show"]):
        main()

    output = capsys.readouterr().out
    assert "不得只凭模型记忆" in output
    assert "Do not rely on model memory alone" not in output


def test_policy_check_exits_nonzero_when_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with patch(
        "sys.argv",
        [
            "factreach",
            "policy",
            "--check",
            "--target",
            "codex",
            "--scope",
            "project",
        ],
    ):
        with pytest.raises(SystemExit) as exc:
            main()

    assert exc.value.code == 1
