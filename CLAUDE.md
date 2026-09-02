# CLAUDE.md

## Project
FactReach — evidence-first Python CLI + library for reading and searching 23 internet channels.
Positioning: policy manager + installer + doctor + multi-backend router. After installation,
agents may call upstream tools directly or use FactReach's web/Douyin entry points.
Repo: github.com/simonlin1212/FactReach | License: MIT | Version: 1.0.0
Derived from github.com/Panniantong/Agent-Reach; preserve LICENSE and NOTICE attribution.

## Commands
- `pip install -e .` — Dev install
- `pytest tests/ -v` — All tests
- `pytest tests/test_cli.py -v` — CLI tests only
- `bash test.sh` — Full integration test (creates venv, installs, runs doctor + channel tests)
- `python -m agent_reach.cli doctor` — Run diagnostics
- `python -m agent_reach.cli install --env=auto` — Read-only environment check
- `factreach install --env=auto --system` — Explicitly allow system changes

## Structure
- `agent_reach/cli.py` — CLI entry point (argparse)
- `agent_reach/core.py` — Core read/search routing logic
- `agent_reach/config.py` — Config management (YAML, env vars)
- `agent_reach/doctor.py` — Diagnostics engine
- `agent_reach/channels/` — One file per platform (twitter.py, reddit.py, youtube.py, etc.)
- `agent_reach/channels/base.py` — Base channel class (all channels inherit from this)
- `agent_reach/integrations/mcp_server.py` — MCP server integration
- `agent_reach/skill/` — OpenClaw skill files
- `agent_reach/guides/` — Usage guides
- `tests/` — pytest tests
- `config/mcporter.json` — MCP tool config

## Conventions
- Python 3.10+ with type hints
- Each channel is a single file in `channels/`, inherits from `BaseChannel`
- Channel contract: must implement `can_handle(url)`, `read(url)`, `search(query)`, `check()` methods
- Use `loguru` for logging, `rich` for CLI output
- Commit format: `type(scope): message` (one commit = one thing)
- All upstream tool calls go through public API/CLI, never hack internals

## Rules
- Public `main` intentionally uses an independent FactReach history from 2026-09-02 onward;
  do not restore upstream commits to the public branch. Preserve upstream copyright and
  licensing attribution in `LICENSE` and `NOTICE`.
- FactReach is a routing and policy layer; external backends remain independently licensed.
- Version in THREE places must match: `pyproject.toml`, `__init__.py`, `tests/test_cli.py`.
- Public brand/CLI/Skill use `FactReach` / `factreach`; internal module and `~/.agent-reach/`
  remain compatible until a separately planned migration.
- Always new branch for changes, PR to main, never push to main directly
- Run `pytest tests/ -v` before committing — all tests must pass
- Cookie-based auth (Twitter, XHS): use Cookie-Editor export method only, no QR scan
- XHS login: Cookie-Editor browser export only (QR will hang)
