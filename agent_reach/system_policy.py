"""Install FactReach's evidence policy into agent instruction files.

The FactReach skill is loaded only after an agent decides to use it, so it
cannot enforce search-before-reasoning on its own.  This module manages a
small, explicit block in CLAUDE.md and/or AGENTS.md, where the rule is visible
to the agent before it starts a task.
"""

from __future__ import annotations

import importlib.resources
import os
import stat
import tempfile
from pathlib import Path

from agent_reach.utils.paths import home_dir

POLICY_START = "<!-- BEGIN AGENT-REACH EVIDENCE-FIRST POLICY -->"
POLICY_END = "<!-- END AGENT-REACH EVIDENCE-FIRST POLICY -->"
MAX_INSTRUCTION_BYTES = 4 * 1024 * 1024
SUPPORTED_TARGETS = ("claude", "codex")


class SystemPolicyError(RuntimeError):
    """Raised when an instruction file cannot be updated safely."""


def _user_config_root(env_name: str, fallback: Path) -> Path:
    raw = os.environ.get(env_name, "").strip()
    root = Path(raw).expanduser() if raw else fallback
    if not root.is_absolute():
        raise SystemPolicyError(f"{env_name} must be an absolute path")
    return root


def load_policy(language: str = "zh") -> str:
    """Load the packaged managed block for ``language``."""

    if language not in {"zh", "en"}:
        raise ValueError("language must be 'zh' or 'en'")
    resource = (
        importlib.resources.files("agent_reach")
        .joinpath("policies")
        .joinpath(f"evidence_first_{language}.md")
    )
    return resource.read_text(encoding="utf-8").strip() + "\n"


def resolve_targets(
    target: str,
    scope: str,
    *,
    cwd: Path | None = None,
    home: Path | None = None,
) -> dict[str, Path]:
    """Return instruction-file paths for a target/scope pair."""

    if target not in {"auto", "claude", "codex", "both"}:
        raise ValueError("unsupported target")
    if scope not in {"project", "user"}:
        raise ValueError("scope must be 'project' or 'user'")

    current_dir = Path.cwd() if cwd is None else Path(cwd)
    user_home = home_dir() if home is None else Path(home)

    if scope == "project":
        codex_override = current_dir / "AGENTS.override.md"
        candidates = {
            "claude": current_dir / "CLAUDE.md",
            "codex": (
                codex_override
                if codex_override.exists()
                else current_dir / "AGENTS.md"
            ),
        }
    else:
        claude_root = _user_config_root(
            "CLAUDE_CONFIG_DIR", user_home / ".claude"
        )
        codex_root = _user_config_root("CODEX_HOME", user_home / ".codex")
        codex_override = codex_root / "AGENTS.override.md"
        candidates = {
            "claude": claude_root / "CLAUDE.md",
            "codex": (
                codex_override if codex_override.exists() else codex_root / "AGENTS.md"
            ),
        }
    if target == "auto":
        if scope == "project":
            detected = tuple(name for name, path in candidates.items() if path.exists())
        else:
            detected = tuple(
                name
                for name, path in candidates.items()
                if path.exists() or path.parent.exists()
            )
        names = detected or SUPPORTED_TARGETS
    else:
        names = SUPPORTED_TARGETS if target == "both" else (target,)
    return {name: candidates[name] for name in names}


def policy_status(path: Path) -> str:
    """Return ``installed``, ``outdated``, ``missing``, or ``broken``."""

    if path.is_symlink():
        return "broken"
    if not path.exists():
        return "missing"
    if not path.is_file():
        return "broken"
    try:
        if path.stat().st_size > MAX_INSTRUCTION_BYTES:
            return "broken"
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return "broken"
    starts = text.count(POLICY_START)
    ends = text.count(POLICY_END)
    if starts == 0 and ends == 0:
        return "missing"
    if starts == 1 and ends == 1 and text.index(POLICY_START) < text.index(POLICY_END):
        start = text.index(POLICY_START)
        end = text.index(POLICY_END, start) + len(POLICY_END)
        managed_block = text[start:end].strip()
        current_blocks = {
            load_policy("zh").strip(),
            load_policy("en").strip(),
        }
        return "installed" if managed_block in current_blocks else "outdated"
    return "broken"


def _merge_policy(existing: str, policy: str) -> str:
    status_start = existing.count(POLICY_START)
    status_end = existing.count(POLICY_END)
    if status_start == 0 and status_end == 0:
        if not existing:
            return policy
        separator = "" if existing.endswith("\n\n") else (
            "\n" if existing.endswith("\n") else "\n\n"
        )
        return existing + separator + policy
    if status_start != 1 or status_end != 1:
        raise SystemPolicyError("instruction file contains incomplete or duplicate policy markers")
    start = existing.index(POLICY_START)
    if existing.index(POLICY_END) < start:
        raise SystemPolicyError("instruction file contains reversed policy markers")
    end = existing.index(POLICY_END, start) + len(POLICY_END)
    return existing[:start] + policy.rstrip("\n") + existing[end:]


def _atomic_write(path: Path, text: str, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        if os.name != "nt":
            os.chmod(temp_path, mode)
        if path.is_symlink():
            raise SystemPolicyError(f"refusing to replace symlink: {path}")
        os.replace(temp_path, path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise


def install_policy(path: Path, *, language: str = "zh") -> str:
    """Append or refresh the managed policy block in one instruction file."""

    path = Path(path)
    if path.is_symlink():
        raise SystemPolicyError(f"refusing to edit symlink: {path}")
    if path.exists() and not path.is_file():
        raise SystemPolicyError(f"instruction target is not a regular file: {path}")
    if path.exists() and path.stat().st_size > MAX_INSTRUCTION_BYTES:
        raise SystemPolicyError(f"instruction file exceeds {MAX_INSTRUCTION_BYTES} bytes: {path}")

    try:
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
    except (OSError, UnicodeError) as exc:
        raise SystemPolicyError(f"could not read instruction file: {path}") from exc

    merged = _merge_policy(existing, load_policy(language))
    if len(merged.encode("utf-8")) > MAX_INSTRUCTION_BYTES:
        raise SystemPolicyError(
            f"managed policy would exceed {MAX_INSTRUCTION_BYTES} bytes: {path}"
        )
    if merged == existing:
        return "unchanged"
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    _atomic_write(path, merged, mode)
    return "updated" if existing else "created"


def remove_policy(path: Path) -> str:
    """Remove only the managed policy block, preserving other instructions."""

    path = Path(path)
    status = policy_status(path)
    if status == "missing":
        return "unchanged"
    if status == "broken":
        raise SystemPolicyError(f"refusing to edit malformed instruction file: {path}")

    existing = path.read_text(encoding="utf-8")
    start = existing.index(POLICY_START)
    end = existing.index(POLICY_END, start) + len(POLICY_END)
    # Preserve every byte outside the managed markers. Blank separator lines
    # may remain, but user-authored indentation and Markdown hard breaks do not
    # get rewritten.
    merged = existing[:start] + existing[end:]

    mode = stat.S_IMODE(path.stat().st_mode)
    _atomic_write(path, merged, mode)
    return "removed"
