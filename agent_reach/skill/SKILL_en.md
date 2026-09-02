---
name: factreach
description: >
  MUST USE when user wants to research/search/look up/find anything on the
  internet — e.g. "research this topic", "do a deep dive on X", "search the
  web for X", "see what people say about X", "look this up".

  Also MUST USE when user mentions any platform or shares any URL/link:
  Twitter/X, Douyin, Weibo, Reddit, Facebook, Instagram, YouTube, GitHub, Bilibili, XiaoHongShu,
  Xiaoyuzhou Podcast, LinkedIn/jobs/recruiting, V2EX, Xueqiu (stocks), RSS,
  Hacker News, public WeChat articles, arXiv/PubMed/Semantic Scholar/
  OpenReview/DBLP, Stack Overflow, or GitHub Trending.

  23 channels, multi-backend routing (open-websearch / OpenCLI / per-platform
  CLIs / APIs). Run `factreach doctor --json` to see which
  backend serves each platform right now.

  NOT for: writing reports/analysis/translation (this skill only FETCHES
  internet content); posting/commenting/liking (write operations); platforms
  that already have a dedicated skill installed (prefer that skill).
metadata:
  homepage: https://github.com/simonlin1212/FactReach
---

# FactReach — internet capability router

23 channels, multiple backends each. **When this skill exists, use it for
these platforms — do not invent your own approach.**

## System-policy boundary

This skill applies only after an agent has already decided to invoke it. It
**cannot by itself force search before the agent answers an external factual
question**. Put that rule in an instruction file loaded at agent startup:
`CLAUDE.md` for Claude Code or `AGENTS.md` for Codex.

During first-time setup, run `factreach policy --check`. If the policy is
missing, inspect the existing instruction file for an equivalent manual rule
before adding a duplicate. If it is truly absent, explain this boundary and
show `factreach policy --show`. Only after the user explicitly approves a
system-config edit, run one of these:

```bash
factreach policy --install --target claude --scope user  # Claude Code
factreach policy --install --target codex --scope user   # Codex
factreach policy --install --target both --scope user    # both
```

Never silently edit `CLAUDE.md` or `AGENTS.md` merely because this skill was invoked.

## Standing rules (apply for the whole session)

1. **Health-check before acting**: for multi-backend/login-backed platforms (XiaoHongShu /
   Weibo / Reddit / Bilibili / Twitter / Facebook / Instagram), run `factreach doctor --json` first.
   Use a populated `active_backend`; `active_backend: null` means Doctor deliberately skipped a
   live probe to avoid browser-cookie reads or remote writes, not that no backend exists. Only when
   the user's task requires that platform, run the reference's read-only command to verify it.
2. **Announce what you use**: say "using factreach, platform X via backend Y"
   before starting.
3. **On failure, follow the retry chains in references/** — never guess
   commands.
4. **For broad research tasks**: start with a live open-websearch query, use
   Exa for semantic expansion, then combine Twitter/Reddit/Hacker News for
   discussions and XiaoHongShu/Bilibili/public WeChat for Chinese context.
5. **Watch versions for the user**: after finishing a substantial
   multi-platform task, run `factreach check-update` (fast, one API call).
   If a new version exists, append one line to your wrap-up: "FactReach
   vX.Y.Z is available — paste this to me to update: 帮我更新 FactReach：
   https://raw.githubusercontent.com/simonlin1212/FactReach/main/docs/update.md".
   Never interrupt the current task to update; never nag about the same version twice.

## Routing table

| User intent | Category | Details |
|---------|------|---------|
| Web / code search | search | [references/search.md](references/search.md) |
| XiaoHongShu / Twitter / Weibo / Bilibili / V2EX / Reddit / Facebook / Instagram | social | [references/social.md](references/social.md) |
| Jobs / LinkedIn | career | [references/career.md](references/career.md) |
| GitHub / code | dev | [references/dev.md](references/dev.md) |
| Web pages / articles / RSS / dynamic pages / real Chrome | web | [references/web.md](references/web.md) |
| YouTube / Douyin / Bilibili / podcast transcripts | video | [references/video.md](references/video.md) |
| Xueqiu / stock quotes | finance | [references/finance.md](references/finance.md) |

## Zero-config quick commands

```bash
# Zero-auth search: run one engine; continue DDG -> Brave -> Bing only on empty/invalid JSON
open-websearch search "query" --limit 10 --engine duckduckgo --json
# See references/search.md for fallback commands and JSON acceptance checks

# Exa semantic-search supplement
mcporter call exa.web_search_exa query="query" numResults=5

# Public communities / papers / technical Q&A (no browser)
opencli hackernews search "query" -f json
opencli arxiv search "query" -f json
opencli stackoverflow search "query" -f json
opencli stackoverflow read QUESTION_ID -f json
opencli github-trending repos -f json

# WeChat needs no WeChat cookie, but currently requires OpenCLI Browser Bridge
opencli weixin search "query" -f json
opencli weixin download --url "ARTICLE_URL" --output /tmp/factreach-weixin -f json

# Read any web page: Jina first; Firecrawl or real Chrome only when selected
factreach web read "URL"
factreach web read "URL" --backend firecrawl
factreach web read "URL" --backend browser-harness

# GitHub search
gh search repos "query" --sort stars --limit 10

# YouTube subtitles (never use yt-dlp for Bilibili; retry chain in video.md)
yt-dlp --write-sub --write-auto-sub --skip-download -o "/tmp/%(id)s" "URL"

# V2EX hot topics
curl -s "https://www.v2ex.com/api/topics/hot.json" -H "User-Agent: factreach/1.0"

# Bilibili search (bili-cli, no login needed)
bili search "query" --type video -n 5

# Douyin video/note: copy, author, playback or image URLs; ASR is video-only
factreach douyin resolve "SHARE_TEXT_OR_URL"
factreach douyin resolve "SHARE_TEXT_OR_URL" --transcribe
```

## Login-backed platforms (pick by doctor's active_backend)

Twitter boundary: cookies saved by `factreach configure twitter-cookies`
are used only by `doctor` to check whether explicit credentials are present.
`doctor` does not run `twitter status` or configure the current shell. Before
calling `twitter` directly, explicitly provide `TWITTER_AUTH_TOKEN` and
`TWITTER_CT0` in the child-process environment without logging their values.

XiaoHongShu boundary: FactReach must not log the user in or read browser
cookies. OpenCLI may use only an existing Chrome session explicitly controlled
by the user. If none exists, do not automate login; use a manual Cookie-Editor
export with xiaohongshu-mcp or a legacy tool instead.

```bash
# Twitter search (twitter-cli preferred; retry chain in social.md)
twitter search "query" -n 10

# Reddit (NO zero-config path — OpenCLI or rdt-cli, login required)
opencli reddit search "query" -f yaml   # desktop
rdt search "query" --limit 10            # legacy/server

# XiaoHongShu (desktop prefers OpenCLI)
opencli xiaohongshu search "query" -f yaml

# Facebook / Instagram (desktop OpenCLI, browser session)
opencli facebook search "query" -f yaml
opencli facebook groups -f yaml
opencli instagram search "query" -f yaml       # user search
opencli instagram user USERNAME -f yaml        # recent posts from one user

# Weibo (desktop OpenCLI, existing user-controlled login session)
opencli weibo hot -f yaml
opencli weibo search "query" -f yaml
opencli weibo post "WEIBO_URL" -f yaml
```

## Environment check

```bash
# Channel availability + which backend serves each platform
factreach doctor --json
```

## Discovering OpenCLI adapters

When the routing table lacks a needed platform or command, run `opencli list`,
then inspect `opencli <platform> --help`. Discovery proves only that an adapter
exists, not that authentication or target content works. Run read-only commands
only when the user's task requires that platform, and require non-empty content.

## Workspace rules

**Never create files in the agent workspace.** Use `/tmp/` for temporary
output and `~/.agent-reach/` for persistent data.

## Detailed references

Read the matching file when you need specifics (commands above cover the
common cases; references hold per-backend command groups, caveats, retry
chains — note: reference docs are written in Chinese, commands are universal):

- [Search](references/search.md) — open-websearch, Exa, Hacker News, public WeChat, scholarly indexes, Stack Overflow, GitHub Trending
- [Social](references/social.md) — XiaoHongShu, Twitter, Weibo, Bilibili, V2EX, Reddit, Facebook, Instagram (multi-backend/login-backed groups)
- [Career](references/career.md) — LinkedIn
- [Dev](references/dev.md) — GitHub CLI
- [Web](references/web.md) — Jina Reader, Firecrawl, browser-harness, RSS
- [Video](references/video.md) — YouTube, Douyin, Bilibili, Xiaoyuzhou
- [Finance](references/finance.md) — Xueqiu quotes, search and market content

## Configure a channel

If a channel needs setup, fetch the install guide:
https://raw.githubusercontent.com/simonlin1212/FactReach/main/docs/install.md

The user only provides cookies / one extension click; the agent does the rest.
