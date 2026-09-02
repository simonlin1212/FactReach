# 网页阅读

通用网页、RSS。

## 通用网页：三层读取顺序

默认按最小权限顺序：**Jina Reader → 已配置的 Firecrawl → 用户明确授权的
browser-harness**。前两层失败时不得暗中打开真实 Chrome；只有用户明确要求操作浏览器，
或命令显式带 `--allow-browser` / `--backend browser-harness` 时才进入第三层。

```bash
# 自动模式：Jina；若 Jina 返回明确反爬页，已配置时尝试 Firecrawl
factreach web read "https://example.com/article"

# 动态网页：显式使用 Firecrawl
factreach web read "https://example.com/app" --backend firecrawl

# 登录、交互或部分反爬页面：显式连接用户真实 Chrome
factreach web read "https://example.com/account" --backend browser-harness

# 允许自动模式在非浏览器后端失败后再打开 Chrome
factreach web read "https://example.com/account" --allow-browser
```

### 第一层：Jina Reader（零鉴权）

```bash
# 读取任意网页内容
curl -s "https://r.jina.ai/URL"

# 示例
curl -s "https://r.jina.ai/https://example.com/article"
```

**适用场景**: 大多数网页可以直接用 Jina Reader 读取。

### 第二层：Firecrawl（动态渲染）

托管版需要 Key；自托管可配置自己的 `/v2` API 地址。Doctor 只检查配置，**不发请求、
不消耗额度**。

```bash
# 托管版，隐藏输入
factreach configure firecrawl-key

# 自托管；HTTP 只允许 localhost/127.0.0.1/::1，远端必须 HTTPS
factreach configure firecrawl-url "http://localhost:3002/v2"
```

Firecrawl 托管版可能计费或消耗额度；不要把它写成零鉴权能力。抓取结果为空或报错时，
应如实报告，不能把“命令成功”当成“内容已取得”。

### 第三层：browser-harness（真实 Chrome）

用于必须登录、点击交互或普通抓取器无法通过的页面。它不需要 API Key，但会复用用户
已经登录的真实 Chrome，因此属于高权限后端：

- `doctor` 和安装过程只检查可执行文件，不连接 Chrome、不读标签页。
- 不替用户自动登录，不保存账号密码。
- 执行前说明将打开真实 Chrome；完成后只引用实际取得的非空页面内容。
- 需要先在 Chrome 开启远程调试；连接失败按 browser-harness 自带 doctor 指引处理。

## Web Reader (MCP)

```bash
# 读取网页内容 (Markdown 格式)
mcporter call web-reader.webReader url="https://example.com"

# 保留图片
mcporter call web-reader.webReader url="https://example.com" retain_images=true

# 纯文本格式
mcporter call web-reader.webReader url="https://example.com" return_format="text"
```

**适用场景**: 需要更精确控制输出格式时使用。

## RSS (feedparser)

```python
python3 -c "
import feedparser
for e in feedparser.parse('FEED_URL').entries[:5]:
    print(f'{e.title} — {e.link}')
"
```

**适用场景**: 订阅博客、新闻源、播客等 RSS feed。

## 选择指南

| 场景 | 推荐工具 |
|-----|---------|
| 通用网页 | Jina Reader (`curl r.jina.ai`) |
| JS 动态网页 | `factreach web read URL --backend firecrawl` |
| 登录/交互/部分反爬页面 | `factreach web read URL --backend browser-harness`（显式授权） |
| 需要图片/格式控制 | web-reader MCP |
| RSS 订阅 | feedparser |
