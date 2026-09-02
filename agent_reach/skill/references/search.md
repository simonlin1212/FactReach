# 搜索工具

默认用 open-websearch 做零鉴权关键词搜索，需要语义扩展时再用 Exa。

## open-websearch（默认）

```bash
# 必须单引擎顺序执行；每次验收 JSON，成功就停止
open-websearch search "query" --limit 10 --engine duckduckgo --json
# 仅在上一条失败或 results 为空时继续：
open-websearch search "query" --limit 10 --engine brave --json
open-websearch search "query" --limit 10 --engine bing --json
```

验收时必须解析 JSON：只有 `status: ok` 且 `data.results` 非空才算成功。
不得只看进程退出码；某些引擎失效时会退出 0 但返回
`partialFailures` 和空结果。

`--engines duckduckgo,brave,bing` 会并发扇出并分配结果条数，**不是回退**，
因此不用它实现优先级。失败链：DuckDuckGo → Brave → Bing → Exa。

## Exa AI 搜索

高质量 AI 搜索引擎，适合查找技术文档、官方示例和相关网页。

```bash
mcporter call exa.web_search_exa query="query" numResults=5
mcporter call exa.web_search_exa query="library API code example" numResults=5
```

### 使用场景

| 场景 | 参数 |
|-----|------|
| 网页搜索 | `web_search_exa(query: "...", numResults: 5)` |
| 技术/代码资料 | `web_search_exa(query: "框架名 API 示例", numResults: 5)` |

> Exa MCP 的 `get_code_context_exa` 已弃用且默认不注册。代码问题也使用
> `web_search_exa`；需要精确搜索仓库内容时，改用 `dev.md` 中的 GitHub 搜索。

### 特点

- 擅长英文内容和技术文档
- 可通过查询词定位官方文档和代码示例
- 结果质量高

## 与其他搜索工具对比

| 工具 | 来源 | 适用场景 |
|-----|------|---------|
| open-websearch | factreach | 默认零鉴权全网搜索，单引擎顺序回退 |
| Exa | factreach | 英文/技术/代码搜索 |
| 智谱搜索 | my-mcp-tools | 中文搜索 |
| GitHub 搜索 | factreach (dev.md) | 仓库/代码搜索 |

## 零鉴权专项源（OpenCLI public）

```bash
# 技术社区
opencli hackernews search "query" -f json
opencli hackernews read ITEM_ID -f json
opencli stackoverflow search "query" -f json
opencli stackoverflow read QUESTION_ID -f json

# 微信公众号公开文章（不需公众号 Cookie，但实测需 Browser Bridge）
opencli weixin search "query" -f json
# 读搜索返回的公开文章；产物写入 /tmp，不污染工作区
opencli weixin download --url "ARTICLE_URL" --output /tmp/factreach-weixin -f json

# 论文：按任务选源，不要把五个库无差别全打一遍
opencli arxiv search "query" -f json
opencli pubmed search "query" -f json
opencli semanticscholar search "query" -f json
opencli openreview search "query" -f json
opencli dblp search "query" -f json

# 热门仓库
opencli github-trending repos -f json
```

除公众号外，上述命令走公开数据源，不需 Cookie 或 Chrome 扩展。公众号不需
公众号 Cookie，但 OpenCLI 当前会在未连接 Browser Bridge 时返回 `BROWSER_CONNECT`。
所有渠道仍以本次命令
返回的非空内容为验收标准，不能因为 `doctor` 看到 CLI 可执行就把具体
上游站点说成已实时验证。

> 2026-09 实跑边界：arXiv、PubMed、OpenReview、DBLP 可匿名返回；
> Semantic Scholar 匿名额度很低，可返回 HTTP 429。遇到 429 时先切其他论文库；
> 确实要用 Semantic Scholar 再配其官方免费 API Key，不得把它宣称为始终零鉴权。
