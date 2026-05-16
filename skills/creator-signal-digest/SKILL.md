---
name: creator-signal-digest
description: 生成「创作者信号雷达」周报：在不使用 X API 的前提下，用 opencli 的只读 Google/X 搜索或公开抓取方式扫描指定 AI/创作者账号过去 7 天内容，按 AI 实操、副业思路、认知探索、AI 趋势分析四类筛选高价值信号，产出结构化中文 Markdown 周报。当用户要每周创作者信号雷达、多维 X 内容扫描、AI 创作者一周动态、实操/副业/认知/趋势综合观察时，必须使用本 skill。若用户只要高纯度 AI 实操精选，改用 ai-influence-digest。
---

# 创作者信号雷达

目标：把“刷一周创作者 X 动态”变成可复用的多维信号雷达。

本 skill 不替代 `ai-influence-digest`。老 skill 继续做高纯度 AI 实操精选；本 skill 关注同一批创作者释放的执行价值、判断价值和机会价值。

## 约束

1. 禁止使用 X API。
2. 允许使用只读的 `opencli google search`、`opencli twitter search`、X 公共 syndication timeline、X 官方 `oEmbed` 和人工提供的 seed URLs。
3. 涉及 `opencli` 的发现步骤必须在系统环境执行，因为它依赖本机 Chrome Profile 和 Browser Bridge。
4. 不修改 `ai-influence-digest` 的文件或行为。
5. 第一版保留人工编辑判断，自动打分只用于候选排序。

## 快速流程

### 0. 准备账号池

默认账号列表：`references/accounts.txt`

每行一个 handle，不带 `@`。可以按需删减、追加或替换为用户提供的账号池。

### 1. 扫描候选内容

使用脚本抓取过去 N 天候选推文，只拿 URL 和公开网页文本。

默认周报命令：

```bash
python3 scripts/scan_x_weekly.py \
  --accounts references/accounts.txt \
  --days 7 \
  --outdir ./output/creator-signal-digest
```

后端选择：

| 场景 | 推荐后端 | 原因 |
|---|---|---|
| 周报，账号安全优先 | `opencli-google` | 不依赖 X 登录，适合 7 天窗口 |
| 周报，覆盖率优先 | `auto` | Google 不足时自动回退 |
| 日报或近期内容 | `opencli-twitter` | 时效性更好，但依赖已登录 X 的 Chrome Profile |
| 已有链接列表 | `none` 加 `--seed-urls` | 跳过发现阶段，只做抓取和排序 |

输出：

1. `candidates.json`，结构化候选列表。
2. `candidates.md`，便于人工扫读的候选清单。

### 2. 按信号标准筛选

读取 `references/filters.md`。

从候选中筛选 8 到 16 条。每条至少满足一种价值：

1. 执行价值，能立刻试。
2. 判断价值，能提升理解。
3. 机会价值，能提示副业、产品或市场机会。

一条内容可以内部打多个标签，但最终周报里只归入一个主栏目。

### 3. 生成中文周报

读取 `references/report-template.md`，按固定结构生成：

1. 本周总览。
2. AI 实操。
3. 副业思路。
4. 认知探索。
5. AI 趋势分析。
6. 本周最值得跟进的 3 个信号。
7. 下周观察问题。

栏目可以为空。宁缺毋滥，不为了凑数降低信号密度。

### 4. 邮件发送

第一版默认只产出 Markdown。用户明确要求发送邮件时，使用 `send-email` skill 发送最终周报文件。

## 栏目判断

### AI 实操

放入可以马上尝试的工具、工作流、Prompt、教程、模板或方法步骤。

核心问题：看完以后，我能不能马上试一次？

### 副业思路

放入能启发一人公司、产品切口、变现路径、获客方式或分发策略的内容。

核心问题：看完以后，我是不是更容易发现一个机会？

### 认知探索

放入能改变用户对 AI、创作、工作方式、个人能力或长期选择理解的观点和框架。

核心问题：看完以后，我是不是更会判断了？

### AI 趋势分析

放入模型能力、产品格局、平台规则、创作者生态、工具链或用户行为变化。

核心问题：这件事接下来可能如何影响我的选择？

## 编辑规则

1. 每条内容必须解释为什么值得看，不能只摘要。
2. 每条必须保留原始推文链接。
3. 每条建议 120 到 220 字。
4. 总条数建议 8 到 16 条。
5. 如果某个栏目没有高质量内容，可以少于 2 条或为空。
6. 最后必须给出 3 个最值得跟进的信号和 3 个下周观察问题。

## 资源

1. `references/accounts.txt`，默认账号池。
2. `references/filters.md`，筛选标准和分类规则。
3. `references/report-template.md`，中文周报模板。
4. `scripts/scan_x_weekly.py`，候选内容扫描脚本。
5. `DESIGN.md`，设计背景和边界。

