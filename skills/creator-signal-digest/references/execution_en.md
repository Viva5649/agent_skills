# 英语圈执行步骤

## 0. 准备账号池

账号文件：`references/accounts_en.txt`

每行一个 handle，不带 `@`。可以按需删减、追加或替换。

## 1. 扫描候选内容

使用脚本抓取过去 N 天候选推文。默认使用 X API 后端抓取账号 timeline，再在本地打分筛选。

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

**重要：不要手动检查环境变量来判断 API key 是否存在。始终使用默认的 `--discover-backend x-api`，脚本内置的 `_get_env_zsh()` 会自动从 `~/.zshrc` 回退加载 key。不要主动降级到 `auto`。**

后端选择：

| 场景 | 推荐后端 | 原因 |
|------|---------|------|
| 周报默认 | `x-api` | 不依赖 Chrome 登录态，优先读取 `GETX_API_KEY`，回退由脚本自动处理 |
| API 自动选择 | `x-api --x-api-backend auto` | 依次尝试 GetXAPI、twitterapi.io、官方 X Bearer Token |
| 账号级回退 | `--x-api-fallback-backend opencli-twitter` | 单个账号 API 抓取失败时，只对失败账号补跑 opencli Twitter 搜索 |
| 日报或近期搜索补充 | `opencli-twitter` | 时效性更好，但依赖已登录 X 的 Chrome Profile，容易被 X 限流 |
| 已有链接列表 | `none` 加 `--seed-urls` | 跳过发现阶段，只做抓取和排序 |

输出：

1. `candidates.json`，结构化候选列表。
2. `candidates.md`，便于人工扫读的候选清单。

## 2. 按信号标准筛选

1. 先读取 `references/filters.md`（通用筛选规则）。
2. 再读取 `references/filters_en.md`（英语圈补充标准）。

从候选中筛选 8 到 16 条。每条至少满足一种价值：

1. 执行价值，能立刻试。
2. 判断价值，能提升理解。
3. 机会价值，能提示副业、产品或市场机会。

一条内容可以内部打多个标签，但最终周报里只归入一个主栏目。

## 3. 生成中文周报

读取 `references/report-template.md`，按固定结构生成：

1. 本周总览。
2. AI 实操。
3. 副业思路。
4. 认知探索。
5. AI 趋势分析。
6. 本周最值得跟进的 3 个信号。
7. 下周观察问题。

栏目可以为空。宁缺毋滥，不为了凑数降低信号密度。

### 栏目判断

#### AI 实操

放入可以马上尝试的工具、工作流、Prompt、教程、模板或方法步骤。英语圈额外侧重开源可复现和跨语言迁移性。

核心问题：看完以后，我能不能马上试一次？

#### 副业思路

放入能启发一人公司、产品切口、变现路径、获客方式或分发策略的内容。英语圈降权处理，只有具备跨市场迁移价值的才入选。

核心问题：看完以后，我是不是更容易发现一个机会？

#### 认知探索

放入能改变对 AI、创作、工作方式、个人能力或长期选择理解的观点和框架。英语圈侧重一线研究者和核心建设者的判断。

核心问题：看完以后，我是不是更会判断了？

#### AI 趋势分析

放入模型能力、产品格局、平台规则、创作者生态、工具链或用户行为变化。英语圈侧重模型能力变化、研究前沿和平台规则调整。

核心问题：这件事接下来可能如何影响我的选择？

### 编辑规则

1. 每条内容必须解释为什么值得看，不能只摘要。
2. 每条必须保留原始推文链接。
3. 每条建议 120 到 220 字。
4. 总条数建议 8 到 16 条。
5. 如果某个栏目没有高质量内容，可以少于 2 条或为空。
6. 最后必须给出 3 个最值得跟进的信号和 3 个下周观察问题。

产出路径：`output/creator-signal-digest/en/YYYYMMDD_creator_signal_digest.md`

## 4. 邮件发送周报

使用 `send-email` skill 发送。如果没找到 `send-email` skill，输出原因并终止。

发送配置：

- 目标收件人：`chenliang535649@163.com`、`nipuream@163.com`
- 主题：`YYYYMMDD_本周创作者信号雷达（英语圈）`，例如 `20260605_本周创作者信号雷达（英语圈）`
- 正文：用 `--file` 传入最终周报 Markdown 的绝对路径
- SMTP server：`smtp.163.com`
- SMTP port：`465`
- 发送方：`mrnobody212377@163.com`

发送后检查退出码为 0。失败则保留已生成的 Markdown，检查授权码和网络连通性。
