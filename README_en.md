<p align="center"><a href="README.md">简体中文</a> | <b>English</b></p>

<h1 align="center">FactReach</h1>

<p align="center">
  <b>Search first. Answer second. Make claims only after evidence.</b><br>
  <b>23 internet channels:</b> Web Search · X · Xiaohongshu · Douyin · Weibo · Bilibili · YouTube · Reddit · Facebook · Instagram · LinkedIn · GitHub<br>
  GitHub Trending · Hacker News · WeChat Public Articles · Academic Papers · Stack Overflow · Xiaoyuzhou · V2EX · Xueqiu · RSS · Exa Search · Web Reader<br>
  Zero-auth first · Dynamic pages · Real Chrome · Evidence-first system policy
</p>

<p align="center">
  <a href="https://github.com/simonlin1212/FactReach/actions/workflows/pytest.yml"><img src="https://img.shields.io/github/actions/workflow/status/simonlin1212/FactReach/pytest.yml?branch=main&style=flat-square&label=CI" alt="CI"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue?style=flat-square" alt="MIT License"></a>
  <a href="https://github.com/simonlin1212/FactReach/releases"><img src="https://img.shields.io/github/v/release/simonlin1212/FactReach?style=flat-square" alt="Release"></a>
  <a href="https://github.com/simonlin1212/FactReach/stargazers"><img src="https://img.shields.io/github/stars/simonlin1212/FactReach?style=flat-square" alt="GitHub Stars"></a>
  <img src="https://img.shields.io/badge/Channels-23-f08322?style=flat-square" alt="23 Channels">
</p>

<p align="center">
  <a href="#why-factreach">Why FactReach</a> ·
  <a href="#capabilities">Capabilities</a> ·
  <a href="#quick-start">Quick Start</a> ·
  <a href="#channels">Channels</a> ·
  <a href="#security-boundaries">Security</a> ·
  <a href="CHANGELOG.md">Changelog</a>
</p>

---

## Open to AI Roles in Shenzhen

The author is open to AI roles in Shenzhen, particularly in **AI-powered investment research products, Forward Deployed Engineering (FDE), and AI consulting or solutions** at Tencent, other leading technology companies, and financial institutions.

He combines experience in financial institutions with hands-on AI product development, building open-source market data tools and multi-agent systems with **17K+ GitHub stars**.

Contact: [simonlin0423@gmail.com](mailto:simonlin0423@gmail.com)

## Why FactReach

AI agents can write code and analyze documents, yet still answer questions about the real world from model memory. Data changes, pages require authentication, and dynamic content fails to render. The result can sound confident while lacking current evidence.

FactReach addresses both sides of the problem:

1. **Behavior:** place a search-and-verify rule in `CLAUDE.md` or `AGENTS.md`.
2. **Capability:** give the agent a 23-channel, multi-backend router with progressive fallbacks.

A Skill is loaded only after an agent decides to call it, so a Skill cannot enforce search-first behavior by itself. FactReach makes this boundary explicit and provides policy commands that preview, check, install, update, and remove a managed instruction block only with user approval.

## Capabilities

| Capability | What it does |
|---|---|
| 23-channel diagnostics | `factreach doctor --json` reports status, active backend, and remediation for every channel |
| Zero-auth web search | Falls back across DuckDuckGo, Brave, and Bing only after validating non-empty results |
| Social platform routing | Routes X, XiaoHongShu, Weibo, Reddit, Facebook, and Instagram through controlled sessions |
| Douyin link parsing | Extracts copy, author, playback URLs, or image URLs; video transcription is optional |
| Three-tier web reading | Jina Reader → Firecrawl → browser-harness, with real Chrome explicitly selected |
| Public knowledge sources | Hacker News, WeChat public articles, academic indexes, Stack Overflow, GitHub Trending |
| Evidence policy | Manages search-first blocks in `CLAUDE.md` and `AGENTS.md` without overwriting user text |
| Safe defaults | Read-only installation checks, local credentials, private-network blocking, and output scrubbing |

## Quick Start

Give this sentence to an AI agent that can run shell commands:

```text
Install FactReach: https://raw.githubusercontent.com/simonlin1212/FactReach/main/docs/install.md
```

Or install it manually:

```bash
# If Agent-Reach was installed with pipx: pipx uninstall agent-reach
# If it was installed with pip in this Python environment, run the next command.
# This does not delete config, cookies, or tokens under ~/.agent-reach/.
python -m pip uninstall agent-reach
pipx install https://github.com/simonlin1212/FactReach/archive/main.zip

# Read-only environment check by default
factreach install --env=auto

# Run only after explicitly approving system changes
factreach install --env=auto --system

factreach doctor --json
```

For a virtual environment:

```bash
python3 -m venv ~/.factreach-venv
source ~/.factreach-venv/bin/activate
pip install https://github.com/simonlin1212/FactReach/archive/main.zip
factreach doctor
```

Do not install `agent-reach` and `factreach` side by side in the same Python
environment: they intentionally share the `agent_reach` module for compatibility.
Uninstall the old distribution first; the shared configuration directory remains.

See the full [installation guide](docs/install.md) for channel-specific setup and safety boundaries.

## Make Agents Search Before Answering

The search-first policy belongs in an instruction file loaded at agent startup:

- Claude Code: global `~/.claude/CLAUDE.md` or project `CLAUDE.md`
- Codex: global `~/.codex/AGENTS.md` or project `AGENTS.md`

Preview and inspect before writing:

```bash
factreach policy --show
factreach policy --check --target both --scope user
```

Install only after explicit user approval:

```bash
factreach policy --install --target both --scope user
```

The uninstall command removes only the managed block:

```bash
factreach policy --uninstall --target both --scope user
```

## Channels

| Group | Channels | Default route |
|---|---|---|
| Web | Web search, web pages, Exa, RSS | open-websearch, Jina Reader, Exa, feedparser |
| Developer sources | GitHub, GitHub Trending, Hacker News, Stack Overflow | gh CLI and public OpenCLI adapters |
| Academic and public content | arXiv / PubMed / OpenReview / DBLP / Semantic Scholar, WeChat public articles | Public OpenCLI adapters / Browser Bridge |
| Chinese video and communities | Douyin, Bilibili, XiaoHongShu, Weibo, Xiaoyuzhou, V2EX, Xueqiu | Built-in parser, bili-cli, OpenCLI, cookie backends |
| Global video and social | YouTube, X, Reddit, Facebook, Instagram, LinkedIn | yt-dlp, twitter-cli, OpenCLI, MCP |
| Dynamic and authenticated pages | Firecrawl, real Chrome | Firecrawl API and browser-harness |

The registry contains 23 independent channel checks. Availability depends on local dependencies and login state; `factreach doctor --json` is the source of truth.

## Authentication Tiers

| Tier | Typical channels | Requirement |
|---|---|---|
| Zero-auth first | Web search, public pages, GitHub, Bilibili, YouTube, RSS, academic and developer sources, single Douyin links | Public CLIs; no platform cookie |
| Browser session | XiaoHongShu, Weibo, Reddit, Facebook, Instagram | An existing session explicitly controlled by the user |
| User-supplied credentials | Exa, hosted Firecrawl, Groq/OpenAI transcription | Keys stored only in local configuration |

Use a dedicated account for platforms that require cookies or browser sessions. FactReach does not log users in and does not silently scan browser cookies.

The current XiaoHongShu backend order is `OpenCLI` → `xiaohongshu-mcp` → `xhs-cli`. Saved Twitter cookies are used only by Doctor's configuration check; direct `twitter` commands still require `TWITTER_AUTH_TOKEN` and `TWITTER_CT0` in the current process environment. Never place those credentials in command arguments or public logs.

## Web Reading Fallbacks

```text
Public page
  └─ Jina Reader
       └─ Dynamic rendering needed → Firecrawl
            └─ Login or interaction needed → browser-harness (explicit selection)
```

Examples:

```bash
factreach web read "https://example.com"
factreach web read "https://example.com" --backend firecrawl
factreach web read "https://example.com" --backend browser-harness

factreach douyin resolve "Douyin share text or URL"
factreach douyin resolve "Douyin share text or URL" --transcribe
```

## Security Boundaries

- `factreach install` is read-only by default; `--system` is required for dependency installation and configuration writes.
- Cookies and tokens remain in the compatibility directory `~/.agent-reach/`, restricted to the current user and never uploaded.
- Every browser-harness read receives an isolated daemon, BrowserContext, target, and CDP session.
- Real-browser traffic uses a public-DNS-pinned proxy that blocks loopback, private redirects, DNS rebinding, pop-ups, and descendant workers.
- URLs and output fields are scrubbed before rendering; Doctor does not read browser cookies to pretend a backend is available.
- `--dry-run` previews installation and removal actions.

Report vulnerabilities privately through [GitHub Private Vulnerability Reporting](https://github.com/simonlin1212/FactReach/security/advisories/new). See [SECURITY.md](SECURITY.md).

## Compatibility

FactReach maintains configuration and command compatibility with Agent-Reach. To avoid breaking existing installations:

- `factreach` is the primary command; `agent-reach` remains as a compatibility entry point.
- The internal Python module remains `agent_reach`, with `FactReach` added as a class alias.
- Existing `~/.agent-reach/` configuration and credentials continue to work without migration.
- The new Skill directory is named `factreach`, avoiding collisions with the existing Skill.

## Architecture

```text
factreach CLI
├── policy        evidence-first system instructions
├── doctor        23-channel status and backend probes
├── channels      platform capability contracts
├── backends      OpenCLI / Firecrawl / browser-harness
├── config        private local credentials and safe writes
└── skill         agent routing instructions and references
```

Each platform has an ordered backend list. A failed integration can be replaced or reordered without rewriting the whole channel.

## Acknowledgements

Thanks to [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach) and its contributors for the open-source foundation. Copyright, licensing, and third-party attribution details are preserved in [LICENSE](LICENSE) and [NOTICE](NOTICE).

## Contributing

Run the complete local gate before opening a pull request:

```bash
pytest -q
ruff check agent_reach tests
mypy agent_reach
python -m build
```

See [CONTRIBUTING.md](CONTRIBUTING.md). Use the private security channel for vulnerabilities.

## Disclaimer

FactReach provides public-information retrieval, user-authorized session routing, and local tool configuration. It does not guarantee permanent access to third-party platforms. Users are responsible for complying with target-site terms, local laws, account rules, and any costs or risks associated with automation, cookies, or external services.

## Support

If FactReach saves you time, you can buy the author a coffee.

<p align="center">
  <a href="https://buymeacoffee.com/simonlin1212"><img src="./assets/bmc-qr.png" width="180" alt="Buy Me a Coffee"></a>
</p>

## License

[MIT License](LICENSE)

**Author:** Simon Lin · X [@linsizhen](https://x.com/linsizhen) · Email: [simonlin0423@gmail.com](mailto:simonlin0423@gmail.com)
