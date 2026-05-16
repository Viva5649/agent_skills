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

## 前提与约束

1. 禁止使用 X API。
2. 只允许走公开网页和已登录浏览器会话复用路径。
3. 发现阶段可以使用 `opencli google search`、`opencli twitter search` 或 X 公共 syndication。
4. 正文抓取使用 X 官方 `oEmbed`，失败时跳过并记录 warn 日志。
5. 涉及 `opencli` 的发现阶段必须在系统环境执行，不能在沙箱环境执行，因为它需要复用本机 Chrome Profile 和 Browser Bridge 扩展。

## 依赖

1. Python 3.9+
2. `requests`，见 `requirements.txt`
3. `opencli`，默认发现后端，支持 google/twitter search
4. Chrome + Browser Bridge extension
5. 已登录 X 的独立浏览器 Profile，仅 `opencli-twitter` 需要

v0 只负责候选扫描和 Markdown 周报整理，不包含截图海报渲染，因此暂不需要 `jinja2`、`playwright`。

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm install -g @jackwener/opencli
```

再安装 `opencli` 的 Browser Bridge 扩展，并用单独的 Chrome Profile 登录 X。

建议：

1. 使用副号，不用主号。
2. 给 `opencli` 单独建浏览器 Profile。
3. 这个 skill 只会调用只读命令 `opencli google search` 和 `opencli twitter search`。

在 shell 配置中设置 Chrome Profile 名称，脚本启动时会打印确认：

```bash
export OPENCLI_CHROME_PROFILE=<your-alt-account-profile-name>
```

## 快速开始

```bash
python3 scripts/scan_x_weekly.py \
  --accounts references/accounts.txt \
  --days 7 \
  --outdir ./output/creator-signal-digest
```

脚本会生成：

1. `candidates.json`
2. `candidates.md`

之后按 `references/filters.md` 和 `references/report-template.md` 人工编辑最终周报。

建议将最终稿保存为：

`./output/creator-signal-digest/YYYYMMDD_creator_signal_digest.md`

## 实现状态

当前是 v0 版本：

1. 复用老 skill 的账号池和抓取思路。
2. 已改成多维关键词、排除词和打分逻辑。
3. 已提供筛选规则和周报模板。
4. 尚未抽 shared collector。
5. 尚未默认接入邮件发送。
