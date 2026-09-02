<p align="center"><b>简体中文</b> | <a href="README_en.md">English</a></p>

<h1 align="center">FactReach</h1>

<p align="center">
  <b>让 Agent 先查，再答；有证据，再下结论。</b><br>
  23 个互联网渠道 · 零鉴权优先 · 动态网页 · 真实 Chrome · 系统级实证规则
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
  <a href="#为什么需要-factreach">为什么需要</a> ·
  <a href="#核心能力">核心能力</a> ·
  <a href="#快速开始">快速开始</a> ·
  <a href="#支持渠道">支持渠道</a> ·
  <a href="#安全边界">安全边界</a> ·
  <a href="CHANGELOG.md">更新日志</a>
</p>

---

## 作者正在寻找工作机会

作者目前关注腾讯等大型科技企业在深圳的 AI 相关岗位，希望加入一支热爱 AI 开发的团队，继续从事 AI / Agent 产品开发、应用落地及 AI 咨询工作。

联系：[simonlin0423@gmail.com](mailto:simonlin0423@gmail.com)

## 为什么需要 FactReach

Agent 能写代码、做分析，却经常在现实信息上直接依赖模型记忆：数据已经变化、页面需要登录、动态内容抓不到，最终仍可能给出语气确定但缺乏证据的答案。

FactReach 把这个问题拆成两层：

1. **行为层**：把“外部事实必须先搜索、交叉验证”写进 `CLAUDE.md` 或 `AGENTS.md`。
2. **能力层**：为 Agent 提供 23 个渠道、多后端、按轻重分层的搜索与读取路线。

Skill 只有在 Agent 已经决定调用它之后才生效，因此不能代替系统级规则。FactReach 提供可预览、可检测、显式授权后才写入的 policy 命令，把这条边界讲清楚。

## 核心能力

| 能力 | 作用 |
|---|---|
| 23 渠道统一体检 | `factreach doctor --json` 返回每个渠道的状态、后端和修复建议 |
| 零鉴权全网搜索 | DuckDuckGo、Brave、Bing 按真实非空结果回退 |
| 社交平台读取 | X、小红书、微博、Reddit、Facebook、Instagram 等按登录态路由 |
| 抖音链接解析 | 提取视频或图文的文案、作者、播放地址或图片地址；视频可转写 |
| 三层网页读取 | Jina Reader → Firecrawl → browser-harness，真实 Chrome 仅显式启用 |
| 公开知识源 | Hacker News、公众号、论文库、Stack Overflow、GitHub Trending |
| 实证规则管理 | 检查、展示、安装、更新、卸载 `CLAUDE.md` / `AGENTS.md` 中的受管规则块 |
| 安全默认值 | 只读安装检查、凭据本地保存、私网访问阻断、敏感输出清洗 |

## 快速开始

把下面这句话交给支持 Shell 的 AI Agent：

```text
帮我安装 FactReach：https://raw.githubusercontent.com/simonlin1212/FactReach/main/docs/install.md
```

也可以手动安装：

```bash
# 如果用 pipx 装过 Agent-Reach，执行：pipx uninstall agent-reach
# 如果同一 Python 环境用 pip 装过，执行下面这条。
# 这不会删除 ~/.agent-reach/ 里的配置、Cookie 或 Token。
python -m pip uninstall agent-reach
pipx install https://github.com/simonlin1212/FactReach/archive/main.zip

# 默认只检查，不修改系统
factreach install --env=auto

# 明确允许安装外部依赖后再执行
factreach install --env=auto --system

# 查看 23 个渠道当前状态
factreach doctor --json
```

如果使用虚拟环境：

```bash
python3 -m venv ~/.factreach-venv
source ~/.factreach-venv/bin/activate
pip install https://github.com/simonlin1212/FactReach/archive/main.zip
factreach doctor
```

不要在同一个 Python 环境并排安装 `agent-reach` 和 `factreach`：二者为兼容旧用户
共享 `agent_reach` 模块。迁移时先卸载旧发行包，再安装 FactReach；配置目录会保留。

完整安装边界与可选渠道见 [安装指南](docs/install.md)。

## 让 Agent 先搜索再回答

搜索前置规则必须放在 Agent 启动时读取的系统指令文件中：

- Claude Code：全局 `~/.claude/CLAUDE.md`，或项目内 `CLAUDE.md`
- Codex：全局 `~/.codex/AGENTS.md`，或项目内 `AGENTS.md`

先预览和检查：

```bash
factreach policy --show
factreach policy --check --target both --scope user
```

只有在用户明确授权后才写入：

```bash
factreach policy --install --target both --scope user
```

卸载只移除 FactReach 管理的标记块，不覆盖其他系统提示：

```bash
factreach policy --uninstall --target both --scope user
```

## 支持渠道

| 分组 | 渠道 | 默认路线 |
|---|---|---|
| 全网与网页 | 全网搜索、普通网页、Exa、RSS | open-websearch、Jina Reader、Exa、feedparser |
| 开发者信息 | GitHub、GitHub Trending、Hacker News、Stack Overflow | gh CLI、OpenCLI 公开适配器 |
| 学术与公开内容 | arXiv / PubMed / OpenReview / DBLP / Semantic Scholar、公众号 | OpenCLI 公开适配器 / Browser Bridge |
| 中文视频与社区 | 抖音、B站、小红书、微博、小宇宙、V2EX、雪球 | 内置解析、bili-cli、OpenCLI、Cookie 后端 |
| 全球视频与社交 | YouTube、X、Reddit、Facebook、Instagram、LinkedIn | yt-dlp、twitter-cli、OpenCLI、MCP |
| 动态与登录网页 | Firecrawl、真实 Chrome | Firecrawl API、browser-harness |

注册表按独立能力计为 23 个渠道。实际可用状态取决于本机依赖和登录态，始终以 `factreach doctor --json` 为准。

## 鉴权层级

| 层级 | 典型渠道 | 要求 |
|---|---|---|
| 零鉴权优先 | 全网搜索、普通网页、GitHub、B站、YouTube、RSS、论文库、技术社区、抖音单链接 | 安装对应公开 CLI；不需要平台 Cookie |
| 浏览器登录态 | 小红书、微博、Reddit、Facebook、Instagram | 只使用用户已有且明确控制的会话 |
| 用户自备凭据 | Exa、Firecrawl 托管版、Groq/OpenAI 转写 | Key 只保存在本地配置中 |

需要 Cookie 或登录态的平台建议使用专用账号。自动化访问可能触发平台限制；FactReach 不替用户登录，也不会静默扫描浏览器 Cookie。

当前小红书后端顺序为 `OpenCLI` → `xiaohongshu-mcp` → `xhs-cli`。Twitter Cookie 写入兼容配置后只供 Doctor 检查；直接调用 `twitter` 命令时，当前进程仍需显式提供 `TWITTER_AUTH_TOKEN` 和 `TWITTER_CT0`，不得把凭据写进命令行或公开日志。

## 网页读取路线

```text
普通公开页
  └─ Jina Reader
       └─ 动态渲染失败 → Firecrawl
            └─ 必须登录或交互 → browser-harness（显式选择）
```

示例：

```bash
factreach web read "https://example.com"
factreach web read "https://example.com" --backend firecrawl
factreach web read "https://example.com" --backend browser-harness

factreach douyin resolve "抖音分享文本或链接"
factreach douyin resolve "抖音分享文本或链接" --transcribe
```

## 安全边界

- 默认 `factreach install` 只检查环境；`--system` 才允许系统级安装和配置写入。
- Cookie、Token 继续存放在兼容目录 `~/.agent-reach/`，权限限制为当前用户，不上传仓库。
- browser-harness 为每次读取创建隔离的 daemon、BrowserContext、target 与 CDP session。
- 真实浏览器请求经过公共 DNS 固定代理，并阻断私网、回环、DNS rebinding、弹窗和子 worker 越界访问。
- 输出前清理 URL 凭据和敏感字段；`doctor` 不通过读取浏览器 Cookie 来伪装后端可用。
- `--dry-run` 可预览安装和卸载动作。

安全问题请通过 [GitHub Private Vulnerability Reporting](https://github.com/simonlin1212/FactReach/security/advisories/new) 私下提交，不要公开 Issue。详见 [SECURITY.md](SECURITY.md)。

## 兼容性

FactReach 延续 Agent-Reach 的配置与命令兼容性。为了不破坏已有安装：

- 主命令为 `factreach`，同时保留 `agent-reach` 兼容入口。
- Python 内部模块暂时保留 `agent_reach`，并新增 `FactReach` 类别名。
- 原有 `~/.agent-reach/` 配置和凭据继续生效，不自动搬迁。
- 新 Skill 安装目录为 `factreach`，避免与原有 Skill 混淆。

## 架构

```text
factreach CLI
├── policy        系统级实证规则
├── doctor        23 渠道状态与后端探测
├── channels      平台能力契约
├── backends      OpenCLI / Firecrawl / browser-harness
├── config        本地凭据与安全写入
└── skill         Agent 路由说明与参考文档
```

每个平台都有有序后端列表。后端失效时可以调整路由，不必重写整个渠道。

## 致谢

感谢 [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach) 及其贡献者提供的开源基础。版权、许可与第三方组件归属完整保留在 [LICENSE](LICENSE) 和 [NOTICE](NOTICE)。

## 参与贡献

提交代码前请运行：

```bash
pytest -q
ruff check agent_reach tests
mypy agent_reach
python -m build
```

贡献规范见 [CONTRIBUTING.md](CONTRIBUTING.md)。安全问题请走私密报告渠道。

## 免责声明

FactReach 只提供公开信息检索、用户授权会话路由和本地工具配置能力，不保证第三方平台接口永久可用。使用者需要遵守目标网站的服务条款、当地法律及账号规则，并自行承担自动化访问、Cookie 使用和第三方服务费用风险。

## 赞赏

如果 FactReach 节省了检索和配置时间，可以请作者喝杯咖啡。

<p align="center">
  <a href="https://buymeacoffee.com/simonlin1212"><img src="./assets/bmc-qr.png" width="180" alt="Buy Me a Coffee"></a>
</p>

## License

[MIT License](LICENSE)

**作者：** Simon 林 · X [@linsizhen](https://x.com/linsizhen) · 邮箱：[simonlin0423@gmail.com](mailto:simonlin0423@gmail.com)
