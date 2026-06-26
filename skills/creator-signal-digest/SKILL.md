---
name: creator-signal-digest
description: 生成「创作者信号雷达」周报。接受 circle 参数（zh=中文圈/en=英语圈），中文圈侧重 prompt/工具/副业案例，英语圈侧重前沿趋势。当用户要每周创作者信号雷达、多维 X 内容扫描、AI 创作者一周动态时必须使用本 skill。
---

# 创作者信号雷达

关注 X 平台创作者释放的执行价值、判断价值和机会价值。

## circle 参数

调用时必须指定 circle：

| circle | 圈子 | 侧重 |
|--------|------|------|
| `zh` | 中文圈 | 中文 prompt、工具、副业案例、国内创作者生态 |
| `en` | 英语圈 | 英文前沿趋势、模型能力变化、研究动态 |

## 执行流程

根据 circle 参数读取对应执行文件，严格按其步骤运行：

| circle | 执行文件 |
|--------|----------|
| zh | `references/execution_zh.md` |
| en | `references/execution_en.md` |

## 约束

1. 默认优先使用 X API 后端按账号抓取 timeline，读取 `GETX_API_KEY`、`TWITTERAPI_IO_KEY` 或 `X_BEARER_TOKEN`。
2. 单个账号 X API 抓取失败时，默认只对失败账号回退到只读 `opencli twitter search`；也允许使用 `opencli google search`、X 公共 syndication timeline、X 官方 `oEmbed` 和人工提供的 seed URLs。
3. 涉及 `opencli` 的发现步骤必须在系统环境执行，因为它依赖本机 Chrome Profile 和 Browser Bridge。

## 资源

1. `references/accounts_zh.txt` / `references/accounts_en.txt`，分圈账号池。
2. `references/filters.md`，通用筛选标准（两圈共用）。
3. `references/filters_zh.md` / `references/filters_en.md`，各圈补充筛选标准。
4. `references/keywords_zh.json` / `references/keywords_en.json`，分圈关键词配置。
5. `references/report-template.md`，中文周报模板（两圈共用）。
6. `references/execution_zh.md` / `references/execution_en.md`，分圈执行步骤。
7. `scripts/scan_x_weekly.py`，候选内容扫描脚本，默认 `--discover-backend x-api`，并复用 `tech-news-digest/scripts/fetch-twitter.py` 的 X API 后端。
