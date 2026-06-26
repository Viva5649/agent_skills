# creator-signal-digest

`creator-signal-digest` 生成每周创作者信号雷达。

它扫描一批 AI/创作者账号过去 7 天内容，从中筛选四类信号：

1. AI 实操。
2. 副业思路。
3. 认知探索。
4. AI 趋势分析。

它和 `ai-influence-digest` 的边界：

1. `ai-influence-digest` 只做高纯度 AI 实操精选。
2. `creator-signal-digest` 做多维信号雷达，允许执行价值、判断价值和机会价值并存。

## 中文圈 / 英语圈

本 skill 按账号圈子拆为两条独立链路：

| circle | 圈子 | 侧重 | 账号文件 | 关键词 | 筛选补充 |
|--------|------|------|----------|--------|----------|
| `zh` | 中文圈 | prompt/工具/副业案例 | `references/accounts_zh.txt` | `references/keywords_zh.json` | `references/filters_zh.md` |
| `en` | 英语圈 | 前沿趋势/模型能力/研究动态 | `references/accounts_en.txt` | `references/keywords_en.json` | `references/filters_en.md` |

通用规则（两圈共用）：`references/filters.md`、`references/report-template.md`

调用时在 SKILL.md 中指定 circle 参数，自动路由到 `references/execution_zh.md` 或 `references/execution_en.md`。

## 前提与约束

1. 默认使用 X API 后端按账号抓取 timeline，环境变量优先级为 `GETX_API_KEY`、`TWITTERAPI_IO_KEY`、`X_BEARER_TOKEN`。
2. `x-api` 后端复用相邻 `tech-news-digest/scripts/fetch-twitter.py` 的实现，避免重复维护 API 客户端。
3. 单个账号 X API 抓取失败时，默认只对失败账号回退到 `opencli twitter search`。
4. 发现阶段仍可显式回退到 `opencli google search`、`opencli twitter search` 或 X 公共 syndication。
5. URL 发现路径的正文抓取使用 X 官方 `oEmbed`，失败时跳过并记录 warn 日志。
6. 涉及 `opencli` 的发现阶段必须在系统环境执行，不能在沙箱环境执行，因为它需要复用本机 Chrome Profile 和 Browser Bridge 扩展。

## 依赖

1. Python 3.9+
2. `requests`，见 `requirements.txt`
3. `GETX_API_KEY`，推荐的默认 X API key
4. `opencli`，可选回退发现后端，支持 google/twitter search
5. Chrome + Browser Bridge extension，仅 `opencli-twitter` 需要
6. 已登录 X 的独立浏览器 Profile，仅 `opencli-twitter` 需要

v0 只负责候选扫描和 Markdown 周报整理，不包含截图海报渲染，因此暂不需要 `jinja2`、`playwright`。

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm install -g @jackwener/opencli
```

设置 X API key：

```bash
export GETX_API_KEY="your_getxapi_key"
```

如果需要使用 `opencli-twitter` 回退，再安装 `opencli` 的 Browser Bridge 扩展，并用单独的 Chrome Profile 登录 X。

建议：

1. 使用副号，不用主号。
2. 给 `opencli` 单独建浏览器 Profile（可建多个用于轮换，避免 X 限频）。
3. opencli 回退路径只会调用只读命令 `opencli google search` 和 `opencli twitter search`。

### 多 Profile 轮换（推荐）

设置逗号分隔的 profile 列表，脚本会按每 10 个账号切换一个 profile：

```bash
export OPENCLI_CHROME_PROFILES=alt-account-1,alt-account-2
```

如果不设该变量，脚本会自动检测 `opencli profile list` 返回的已连接 profile。
如果自动检测命令失败，或返回了无法解析的非空输出，脚本会报配置错误并退出。
只有 `opencli profile list` 成功且确认没有 profile 时，所有搜索才使用 opencli 默认 profile。

## 快速开始

中文圈：

```bash
python3 scripts/scan_x_weekly.py \
  --accounts references/accounts_zh.txt \
  --keywords-config references/keywords_zh.json \
  --days 7 \
  --lang zh \
  --discover-backend x-api \
  --x-api-backend auto \
  --x-api-fallback-backend opencli-twitter \
  --outdir ./output/creator-signal-digest/zh
```

英语圈：

```bash
python3 scripts/scan_x_weekly.py \
  --accounts references/accounts_en.txt \
  --keywords-config references/keywords_en.json \
  --days 7 \
  --lang en \
  --discover-backend x-api \
  --x-api-backend auto \
  --x-api-fallback-backend opencli-twitter \
  --outdir ./output/creator-signal-digest/en
```

脚本会生成：

1. `candidates.json`
2. `candidates.md`

之后按对应圈子的 `references/execution_{circle}.md` 生成最终周报。

建议将最终稿保存为：

- 中文圈：`./output/creator-signal-digest/zh/YYYYMMDD_creator_signal_digest.md`
- 英语圈：`./output/creator-signal-digest/en/YYYYMMDD_creator_signal_digest.md`

## 邮件发送

最终周报生成后，通过 `send-email` skill 发送给订阅者。具体发送配置见各圈子的 `execution_{circle}.md`。

发送配置：

- 目标收件人：`chenliang535649@163.com`、`nipuream@163.com`
- 主题：`YYYYMMDD_本周创作者信号雷达（{圈子}）`
- 正文：用 `--file` 传入最终周报 Markdown 的绝对路径
- SMTP server：`smtp.163.com`
- SMTP port：`465`
- 发送方：`mrnobody212377@163.com`

发送后检查发送脚本退出码。若发送失败，保留已生成的 Markdown，并检查授权码、网络和 `smtp.163.com:465` 连通性。

## 实现状态

当前是 v0 版本：

1. 已按中文圈/英语圈拆分账号池和关键词配置。
2. SKILL.md 改为薄路由层，按 circle 参数委托执行文件。
3. 脚本支持 `--keywords-config` 覆盖内置关键词。
4. 脚本支持 `--discover-backend x-api`，复用 `tech-news-digest` 的 GetXAPI、twitterapi.io、官方 X API 三种后端，并支持 `--x-api-fallback-backend` 对失败账号做账号级回退。
5. 提供了分圈筛选规则补充和周报执行步骤。
6. 尚未抽 shared collector。
7. 已接入邮件发送流程说明。
