# 金融行情

雪球股票行情、搜索与热门内容。行情可能延迟，不构成投资建议。

## 先检查状态

```bash
factreach doctor --json
```

`xueqiu.active_backend` 有值时按该后端使用；值为 `null` 只表示 Doctor 没有完成
实时内容验证。雪球需要已登录会话或最小 Cookie，不能把 HTTP 400 当成股票不存在。

## OpenCLI（桌面已有 Chrome 登录态时优先）

```bash
# 验证当前登录态
opencli xueqiu whoami -f yaml

# 股票搜索与实时行情
opencli xueqiu search "英伟达" -f yaml
opencli xueqiu stock NVDA -f yaml

# 热门内容与热门股票
opencli xueqiu hot -f yaml
opencli xueqiu hot-stock -f yaml

# 查看全部只读命令
opencli xueqiu --help
```

OpenCLI 只复用用户已经存在且明确控制的浏览器会话。不要自动执行
`opencli xueqiu login`；没有现成登录态时，让用户先在 Chrome 登录，或显式导入
雪球所需的最小 Cookie：

```bash
factreach configure --from-browser chrome --platform xueqiu
```

该配置只读取并保存 `xq_a_token`，不会顺带采集其他平台 Cookie。

## 验收与失败处理

- 以返回股票名称、代码、价格或非空内容列表为成功；退出码 0 但字段为空不算成功。
- HTTP 400 通常是会话/Cookie 问题，不表示股票代码不存在。
- `whoami` 成功而 `stock`/`hot` 失败时，按适配器解析或平台接口问题报告，不要误诊成未登录。
