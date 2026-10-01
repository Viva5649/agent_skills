# agent_skills

个人 Agent Skill 仓库。收录自建 skill，并以 git submodule 方式聚合常用的外部 skill 库。

本文档记录本机（macOS）当前的 skill 全貌，分三层：仓库自建、全局安装、项目级。全局安装的 skill 由 [`skillctl`](#六用-skillctl-管理全局-skill) 按仓库根目录的 `skills.json` 安装，来源仓库以它为准。

- 自建 skill：8 个（`skills/`）
- 全局安装：35 个（`~/.agents/skills/`，`~/.claude/skills/` 下是指向它的软链接）
- 项目级：6 个（`personal_ai_infrastructure/.claude/skills/`）
- 外部聚合：7 个仓库，共 200 个 skill（`third_party/`）

---

## 一、仓库自建 skill（`skills/`）

| Skill | 用途 | 源仓库 | 全局已装 |
|---|---|---|:---:|
| `clarify-life-direction` | 人生方向澄清。回溯经历、澄清愿景、定义反愿景、倒推路径，把「不知道自己想要什么」变成可执行方向 | [Viva5649/agent_skills](https://github.com/Viva5649/agent_skills) | ✅ |
| `clarify-thought` | 命题分解与决策澄清。维特根斯坦 + 苏格拉底 + 波兰尼三层架构，把模糊想法拆成精准指令或清晰决策 | [Viva5649/agent_skills](https://github.com/Viva5649/agent_skills)（原作者 riiiku） | ✅ |
| `create-blueprint` | 生成工程蓝图风格技术图表，支持箭头、连线、关系标注，用于架构图与流程图 | [Viva5649/agent_skills](https://github.com/Viva5649/agent_skills) | ✅ |
| `creator-signal-digest` | 创作者信号雷达周报。扫描中文圈/英语圈 AI 创作者账号，筛选 AI 实操与副业信号 | [Viva5649/agent_skills](https://github.com/Viva5649/agent_skills) | ❌ |
| `explain-concept` | 概念通俗讲解与可视化。输出生活化例子、记忆方法，适合时按概念结构选 mermaid / SVG / HTML 出图 | [Viva5649/agent_skills](https://github.com/Viva5649/agent_skills) | ❌ |
| `optimize-prompt` | 提示词优化。基于 57 个提示词框架选择合适结构，先澄清目标、受众、上下文再改写 | [Viva5649/agent_skills](https://github.com/Viva5649/agent_skills) | ✅ |
| `publish-site` | 管理个人 Vantage 站点，把已准备好的内容转成双主题编辑风格 HTML 报告并发布 | [Viva5649/agent_skills](https://github.com/Viva5649/agent_skills) | ✅ |
| `send-email` | 通过 SMTP 发送邮件，支持 Markdown 转 HTML、附件、多收件人与 CC/BCC | [Viva5649/agent_skills](https://github.com/Viva5649/agent_skills) | ✅ |

> `clarify-thought` 迁移自独立仓库 `Viva5649/clarify-skill`，原作者 riiiku（MIT，署名保留在 `skills/clarify-thought/LICENSE`）。

---

## 二、全局安装 skill（`~/.agents/skills/` 与 `~/.claude/skills/`）

对所有项目生效，Claude Code 和 Codex 看到的是同一份。除 `agent-reach` 和 `ego-browser` 外，都由 skillctl 安装，见「六」。

「`third_party/` 收录」列说明这个 skill 的**上游仓库**在本仓库里能不能直接翻到源码：

- ✅ 上游仓库已作为 submodule 收进 `third_party/`，`cd third_party/xxx` 就能看源码、查历史、跟版本
- ❌ 上游仓库还没收进来，只有装到本机的那一份，想看源码得去 GitHub，清单见「四」的「尚未聚合的上游仓库」
- 本仓库 该 skill 是自建的，正文在 `skills/` 下，没有外部上游

### 官方 / Anthropic

| Skill | 用途 | 源仓库 | `third_party/` 收录 |
|---|---|---|:---:|
| `docx` | Word 文档（.docx/.dotx）创建、读取、编辑，含目录、页眉、修订与批注 | [anthropics/skills](https://github.com/anthropics/skills) | ✅ |
| `pdf` | PDF 读取、合并、拆分、加水印、填表单、加解密、OCR | [anthropics/skills](https://github.com/anthropics/skills) | ✅ |
| `pptx` | PPT（.pptx/.potx）创建、解析、编辑，含模板、版式、演讲者备注 | [anthropics/skills](https://github.com/anthropics/skills) | ✅ |
| `xlsx` | 电子表格（.xlsx/.csv/.tsv）创建、编辑、公式、图表、脏数据清洗 | [anthropics/skills](https://github.com/anthropics/skills) | ✅ |
| `frontend-design` | 前端视觉设计指导，审美方向、排版、避免模板化默认样式 | [anthropics/skills](https://github.com/anthropics/skills) | ✅ |
| `anthropic-skill-creator` | 创建、修改、优化 skill，跑 eval 测试与描述调优。上游名为 `skill-creator`，改名以区分 Codex 自带的同名 skill | [anthropics/skills](https://github.com/anthropics/skills) | ✅ |

### 工程 / 方法论

| Skill | 用途 | 源仓库 | `third_party/` 收录 |
|---|---|---|:---:|
| `agent-browser` | 浏览器自动化 CLI，导航、填表、截图、抓数据、测试 Web 与 Electron 应用 | [vercel-labs/agent-browser](https://github.com/vercel-labs/agent-browser) | ❌ |
| `ego-browser` | ego lite 浏览器自动化，可复用用户已登录的网站与上下文，做网页操作、表单填写、截图、Web 应用测试 | [ego lite](https://lite.ego.app/)（随应用安装，非 GitHub） | ❌ |
| `qiaomu-goal-meta-skill` | 把模糊任务转成结构化 Codex `/goal` 指令，含验收标准与边界条件 | [joeseesun/qiaomu-goal-meta-skill](https://github.com/joeseesun/qiaomu-goal-meta-skill) | ❌ |
| `neat-freak` | 知识收尾。把项目文档、CLAUDE.md/AGENTS.md、agent 记忆和当前代码实际行为对齐 | [KKKKhazix/khazix-skills](https://github.com/KKKKhazix/khazix-skills) | ✅ |
| `codebase-documenter` | 代码库文档撰写。README、架构说明、API 文档、上手指南 | [ailabs-393/ai-labs-claude-skills](https://github.com/ailabs-393/ai-labs-claude-skills) | ❌ |
| `spec-miner` | 逆向工程。从无文档的遗留代码库里反推规格、依赖图与业务逻辑 | [jeffallan/claude-skills](https://github.com/jeffallan/claude-skills) | ❌ |
| `smell` | 架构坏味道与复杂度热点检测，输出反模式违规的 markdown 报告 | [smallnest/goal-workflow](https://github.com/smallnest/goal-workflow) | ❌ |

### 信息获取 / 研究

| Skill | 用途 | 源仓库 | `third_party/` 收录 |
|---|---|---|:---:|
| `agent-reach` | 全网调研入口。13 个平台多后端路由，覆盖小红书、X、B 站、Reddit、V2EX、领英等 | [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach) | ❌ |
| `hv-analysis` | 横纵分析法深度研究。纵轴追生命历程，横轴做竞品对比，产出 PDF 报告 | [KKKKhazix/khazix-skills](https://github.com/KKKKhazix/khazix-skills) | ✅ |
| `aihot` | 查询 AIHOT 中文 AI 资讯、精选、热点与日报，走匿名只读 API | [KKKKhazix/khazix-skills](https://github.com/KKKKhazix/khazix-skills) | ✅ |
| `notecraft` | NotebookLM 自动化。建笔记本、加源、生成播客/视频/幻灯片/闪卡 | [icebear0828/notebooklm-client](https://github.com/icebear0828/notebooklm-client) | ❌ |
| `youtube-downloader` | 基于 yt-dlp 下载 YouTube 及 1000+ 站点视频 | [crazynomad/skills](https://github.com/crazynomad/skills) | ❌ |

### 内容创作 / 设计

| Skill | 用途 | 源仓库 | `third_party/` 收录 |
|---|---|---|:---:|
| `humanizer` | 改写 AI 腔文本，去除套话、虚高措辞、重复结构，保持原意不变 | [blader/humanizer](https://github.com/blader/humanizer) | ❌ |
| `guizang-ppt-skill` | 横向翻页网页 PPT（单 HTML），含 WebGL 背景与演讲者视图，两种风格 | [op7418/guizang-ppt-skill](https://github.com/op7418/guizang-ppt-skill) | ❌ |
| `huashu-design` | HTML 高保真原型、幻灯片、动画、可视化，新设计强制先出三稿供选 | [alchaincyf/huashu-design](https://github.com/alchaincyf/huashu-design) | ❌ |
| `baoyu-article-illustrator` | 文章配图。分析结构定位需要插图的位置，按类型 × 风格 × 配色三维生成 | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) | ✅ |
| `baoyu-cover-image` | 文章封面图。类型、配色、渲染、文字、情绪五维组合，支持 2.35:1 / 16:9 / 1:1 | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) | ✅ |
| `show-me` | 把当前话题讲成图。按内容挑最小够用的形式，伪代码、diff 草图、mermaid 或单页 HTML | [humanlayer/skills](https://github.com/humanlayer/skills) | ❌ |
| `create-blueprint` | 工程蓝图风格技术图表 | [Viva5649/agent_skills](https://github.com/Viva5649/agent_skills) | 本仓库 |
| `publish-site` | Vantage 站点报告发布 | [Viva5649/agent_skills](https://github.com/Viva5649/agent_skills) | 本仓库 |

### 个人决策 / 思考

| Skill | 用途 | 源仓库 | `third_party/` 收录 |
|---|---|---|:---:|
| `clarify-thought` | 命题分解与决策澄清 | [Viva5649/agent_skills](https://github.com/Viva5649/agent_skills) | 本仓库 |
| `clarify-life-direction` | 人生方向澄清 | [Viva5649/agent_skills](https://github.com/Viva5649/agent_skills) | 本仓库 |
| `optimize-prompt` | 提示词优化 | [Viva5649/agent_skills](https://github.com/Viva5649/agent_skills) | 本仓库 |

### Skill 管理自身

| Skill | 用途 | 源仓库 | `third_party/` 收录 |
|---|---|---|:---:|
| `find-skills` | 发现与安装 skill，响应「有没有能做 X 的 skill」类提问 | [vercel-labs/skills](https://github.com/vercel-labs/skills) | ❌ |

### 其他

| Skill | 用途 | 源仓库 | `third_party/` 收录 |
|---|---|---|:---:|
| `send-email` | SMTP 发信 | [Viva5649/agent_skills](https://github.com/Viva5649/agent_skills) | 本仓库 |

### gstack（选择性安装）

| Skill | 用途 | 源仓库 | `third_party/` 收录 |
|---|---|---|:---:|
| `gstack` | gstack skill 套件的路由入口 | [garrytan/gstack](https://github.com/garrytan/gstack) | ✅ |
| `gstack-office-hours` | YC Office Hours 两种模式，帮你想清楚一个东西值不值得做 | [garrytan/gstack](https://github.com/garrytan/gstack) | ✅ |
| `gstack-plan-ceo-review` | CEO / 创始人视角的方案评审，推动放大格局与重新审视范围 | [garrytan/gstack](https://github.com/garrytan/gstack) | ✅ |
| `gstack-plan-eng-review` | 工程经理视角的方案评审，审架构与实施计划 | [garrytan/gstack](https://github.com/garrytan/gstack) | ✅ |

> 上游共 61 个 skill，这里只装了需要的几个，装法见「六」的 gstack 小节。

---

## 三、项目级 skill（`personal_ai_infrastructure/.claude/skills/`）

仅在 personal_ai_infrastructure 仓库内生效。目前只保留自建 skill，外部来源的已全部下放到全局安装或移除。

这一层同时镜像在同仓库的 `.agents/skills/`，两份内容必须逐字节一致（该仓库的 FATAL-008）。镜像靠人工维护，改一份忘了改另一份不会有任何提示，所以 `run-maintenance` 每天会跑一次 `diff` 校验，发现漂移只报告不自动修复，同步方向由本人决定。

| Skill | 用途 |
|---|---|
| `analyze-article` | 文章深度分析。核心观点、论证审视、可复用框架提取、写作技巧与说服机制拆解 |
| `analyze-side-hustle` | 副业思路个性化分析。结合本体画像与已有结论，判断外部赚钱机会与自身的匹配度 |
| `prepare-lesson` | 异步学习备课。把剪藏网页或长文加工成适配水平的教学材料，归档供碎片时间阅读 |
| `research-purchase` | 购物决策调研。200 元以上不熟悉品类，B 站横评加图文源交叉验证，输出候选对比与推荐 |
| `transcribe-video` | 视频音频转文字。优先取现有字幕，回落 yt-dlp 抽音频加 mlx-whisper 转写 |
| `run-maintenance` | 仓库定时维护。每日简报、任务归档、每周内容数据、每月投资纪律检查、双份同步校验 |

全部为自建，源仓库均为 [Viva5649/personal_ai_infrastructure](https://github.com/Viva5649/personal_ai_infrastructure)，不在本仓库聚合范围内。

---

## 四、外部 skill 库（`third_party/`，git submodule）

| 目录 | 源仓库 | skill 数 | 说明 |
|---|---|---:|---|
| `mattpocock-skills` | [mattpocock/skills](https://github.com/mattpocock/skills) | 37 | TypeScript 工程实践，TDD、领域建模、代码评审、架构改进 |
| `superpowers` | [obra/superpowers](https://github.com/obra/superpowers) | 14 | 系统化调试、TDD、并行 agent 调度、worktree 工作流 |
| `gstack` | [garrytan/gstack](https://github.com/garrytan/gstack) | 61 | 全栈开发流水线，规划、评审、QA、iOS、部署、eval |
| `compound-engineering` | [EveryInc/compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) | 40 | `ce-*` 复利工程系列，从 brainstorm 到 ship 的完整闭环 |
| `khazix-skills` | [KKKKhazix/khazix-skills](https://github.com/KKKKhazix/khazix-skills) | 6 | 卡兹克写作、横纵分析、AIHOT 资讯 |
| `baoyu-skills` | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) | 22 | 宝玉系列，翻译、配图、信息图、多平台发布 |
| `anthropics-skills` | [anthropics/skills](https://github.com/anthropics/skills) | 20 | 官方 skill，Office 文档、前端设计、MCP builder |

### 尚未聚合的上游仓库

以下仓库已有 skill 装在本机，但还没收进 `third_party/`：

| 源仓库 | 涉及 skill |
|---|---|
| [vercel-labs/agent-browser](https://github.com/vercel-labs/agent-browser) | `agent-browser` |
| [ego lite](https://lite.ego.app/)（应用内置，无公开仓库） | `ego-browser` |
| [vercel-labs/skills](https://github.com/vercel-labs/skills) | `find-skills` |
| [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach) | `agent-reach` |
| [icebear0828/notebooklm-client](https://github.com/icebear0828/notebooklm-client) | `notecraft` |
| [crazynomad/skills](https://github.com/crazynomad/skills) | `youtube-downloader` |
| [blader/humanizer](https://github.com/blader/humanizer) | `humanizer` |
| [op7418/guizang-ppt-skill](https://github.com/op7418/guizang-ppt-skill) | `guizang-ppt-skill` |
| [alchaincyf/huashu-design](https://github.com/alchaincyf/huashu-design) | `huashu-design` |
| [joeseesun/qiaomu-goal-meta-skill](https://github.com/joeseesun/qiaomu-goal-meta-skill) | `qiaomu-goal-meta-skill` |
| [ailabs-393/ai-labs-claude-skills](https://github.com/ailabs-393/ai-labs-claude-skills) | `codebase-documenter` |
| [jeffallan/claude-skills](https://github.com/jeffallan/claude-skills) | `spec-miner` |
| [smallnest/goal-workflow](https://github.com/smallnest/goal-workflow) | `smell` |
| [humanlayer/skills](https://github.com/humanlayer/skills) | `show-me` |

### 拉取与更新

```bash
git submodule update --init --recursive
```

```bash
git submodule update --remote --merge
```

> 其中 5 个仓库带 `package.json`（gstack、compound-engineering、baoyu-skills、mattpocock-skills 使用 bun 或 npm）。仅在需要运行这些仓库自身的脚本时才需安装依赖，日常读取 skill 不需要。

---

## 五、状态说明

| 项 | 状态 |
|---|---|
| `creator-signal-digest`、`explain-concept` | 有意只留在仓库内，不做全局安装 |
| `ego-browser` | 由 ego lite 应用安装，两个全局目录下都是指向 `~/.local/share/ego/ego-skills` 的软链接，实体在应用包内，随应用升级，不归 skillctl 管，也无法收进 `third_party/` |
| `agent-reach` | 由 Agent-Reach 自己的命令行工具安装，skill 版本要和工具版本对应，不归 skillctl 管 |
| 全局与 `third_party/` 内容重复 | 预期行为，非问题。`third_party/` 的定位是集中管理与查阅上游仓库，全局 skill 由 skillctl 从上游仓库独立安装，两者各司其职 |

### README 同步校验

[`scripts/check-readme-sync.py`](scripts/check-readme-sync.py) 负责把 README 里可机械推导的部分对齐。

```bash
./scripts/check-readme-sync.py
```

校验六项：三层的 skill 名单、头部计数、`third_party/` 各仓库的 skill 数、全局 skill 的源仓库、自建层的「全局已装」列、全局层的「`third_party/` 收录」列与「尚未聚合的上游仓库」表。

全局层以 `skills.json` 里在装的条目为准，再加上脚本里登记的非托管 skill（`agent-reach`、`ego-browser`），不扫描本机目录，所以在哪台电脑上校验结果都一样。本机实际装的和清单是否一致，由 `skillctl check` 负责。项目级默认读 `~/Desktop/personal_ai_infrastructure`，可用 `PAI_ROOT` 覆盖，目录不存在时跳过并打印提示。

不校验也不生成用途描述和分类分组，这两项是人工撰写的。脚本只读，发现漂移时逐条打印并以退出码 1 结束。personal_ai_infrastructure 仓库的 `run-maintenance` 每天会调一次。

---

## 六、用 skillctl 管理全局 skill

[`scripts/skillctl.py`](scripts/skillctl.py) 从 GitHub 拉取 skill，装到 `~/.agents/skills/<安装名>/`（Codex 读取），并在 `~/.claude/skills/<安装名>` 建软链接（Claude Code 读取）。只依赖 git 和系统自带的 Python 3.9 以上版本。第一次运行时会自动创建 `~/.local/bin/skillctl`，之后直接用命令名。

装哪些 skill、叫什么名字、每个上游仓库用哪个提交，都记在仓库根目录的 `skills.json` 里。它只通过命令修改，不要手工编辑。

| 位置 | 内容 |
|---|---|
| `skills.json` | 清单，随本仓库分发 |
| `~/.local/share/agent-skills/repos/<owner>/<repo>/` | 上游仓库的本机副本，浅 clone，只含清单记录的那个提交 |
| `~/.agents/skills/<安装名>/` | skill 实体，内含标记文件 `.skillctl.json` |
| `~/.claude/skills/<安装名>` | 指向上一行目录的软链接 |

本仓库 `third_party/` 下的子仓库只用来阅读上游源码，不参与安装。

### 设计原则

改 skillctl 时以这几条为准，后面各节的具体规则都是它们的展开。新加的行为和其中某条冲突时，先改原则，再改代码。

1. **清单是唯一事实来源。** 装什么、叫什么、每个上游仓库用哪个提交，只看 `skills.json`，它只通过命令修改。sync 让本机状态向清单靠拢，重复运行结果不变。
2. **只动自己装的东西。** 靠标记文件 `.skillctl.json`，或指向仓库副本的软链接，认出哪些是 skillctl 装的。未托管的 skill 不改、不删、不写进清单，只列出来。
3. **不覆盖你的改动。** 手改过的 skill 只报告，不覆盖也不删除；仓库副本有改动时不切换版本。
4. **名字先到先得，所有入口用同一套判断。** 已经装上的 skill 不会因为后来者改名。add 和 sync 新装前调用同一个检查，不过就两处都不装；结果不取决于在哪个目录运行，当前项目的 skill 目录只在 add 时额外检查。
5. **几个 Agent 看到同一份。** 实体放在 `~/.agents/skills`，`~/.claude/skills` 里是指向它的软链接，SKILL.md 的 `name:` 改写成安装名。
6. **版本可复现。** 清单为每个上游仓库记录一个提交，两台电脑装同一版本。只有 update 会升级已用的仓库；add 一个新仓库时取默认分支的最新提交。
7. **合并不丢改动。** skill 条目和仓库版本分开逐条合并，取 `updated_at` 较晚的一条，删除留下 `removed` 记录。只有主力机推送，副机靠拷文件把清单传回。
8. **失败只影响出问题的那一项。** 单个 skill 或仓库出错只报告它自己，其余照常完成；网络卡住时会超时退出，不会一直挂着。
9. **依赖最少。** 单个 Python 文件，只需要 git 和 Python 3.9 标准库。

### 常用命令

| 命令 | 作用 |
|---|---|
| `skillctl add owner/repo` | 列出仓库里的 skill，输入编号挑选安装 |
| `skillctl add owner/repo --skill a,b [--as 名字 \| --prefix 前缀] [--link]` | 非交互安装，按 name 或仓库内路径指定。对已装的 skill 带 `--as` 就是改名 |
| `skillctl remove 安装名` | 卸载，并在清单里标记为已删除 |
| `skillctl sync` | 拉取本仓库、合并清单，让本机安装与清单一致，最后列出未托管的 skill |
| `skillctl merge 文件 [--yes]` | 把另一台电脑的 `skills.json` 合并进来，先列出改动，确认后再执行 |
| `skillctl update [owner/repo]` | 拉取上游最新版本，列出有变化的文件，重装有变化的 skill，并把新版本记进清单 |
| `skillctl list` | 列出托管的 skill，以及两个全局目录里未托管的 skill；能查到来源的会给出纳入管理的 add 命令 |
| `skillctl check` | 只读检查：清单与安装是否一致、重名、手改、失效软链接、上游更新 |

`add`、`remove`、`update`、`merge` 执行前都会先做一次 `sync`。

### 版本

每个上游仓库用哪个提交，记在 `skills.json` 的 `repos` 里。sync 按记录的提交安装，所以两台电脑装的是同一个版本；只有 update 会改这条记录。

add 一个清单里还没有的仓库时，取默认分支的最新提交并记下来。同一仓库已经有 skill 在用时，沿用记录的提交，免得顺带升级已装的那些；想装最新的，先运行 `skillctl update owner/repo`。

### 命名规则

- 默认沿用上游的 name。安装时会拦截四种情况：和清单里的 skill 重名；和本机已有目录重名，`~/.agents/skills`、`~/.claude/skills`、`~/.codex/skills` 和当前项目的 skill 目录都算，清单之外的也算；命中保留名（常见泛名、Claude Code 和 Codex 自带的 skill 名）；不符合 Agent Skills 命名规范。
- 遇到重名时用 `--as` 起别名，或用 `--prefix` 加前缀，前缀优先用项目名。交互安装一次选了多个时，先问要不要统一加前缀，加完仍冲突的逐个提示输入别名，直接回车跳过这一个；非交互安装跳过冲突的那个，其余照装。
- 已经装上的 skill 不会因为后来者改名；安装名写进 SKILL.md 的 `name:`，所以两个工具里看到的名字一致。
- 手改过的 skill 不会被 sync、update、remove 覆盖或删除，只会被报告。
- sync 新装清单里的 skill 时做同样的检查：命名规范、保留名，以及 `~/.agents/skills`、`~/.claude/skills`、`~/.codex/skills` 里的同名目录。任何一项不过就两处都不装，只报告冲突，你自己的 skill 保持原样。当前项目的 skill 目录只在 add 时检查，sync 不看，免得装不装取决于在哪个目录运行。已经装上的 skill 不再重新检查，之后出现的同名目录由 `skillctl check` 报告。

### 在新电脑上安装

1. `git clone https://github.com/Viva5649/agent_skills.git`，放在哪里都可以。
2. 本机已有同名 skill 目录的，先移到备份目录。
3. `python3 <仓库路径>/scripts/skillctl.py sync`，按 `skills.json` 装齐。本机已有、清单里没有的 skill 不会被改动，也不会写进清单，sync 结束时会列出来，能查到来源的附带纳入管理的命令。
4. `skillctl check`。

### 两台电脑之间同步

- **主力机**：增删或 update 之后，提交并推送 `skills.json`。其他电脑下次运行任意 skillctl 命令时就会拿到，并切到同一版本。
- **不能推送的副机**：增删只改它本地的 `skills.json`，不要在副机的 clone 里提交，更新仓库用 `skillctl sync`。把副机的 `skills.json` 拷到主力机任意位置，运行 `skillctl merge <文件>`，再提交推送。副机下次 sync 后，`git diff skills.json` 变空，说明改动已经送达。

合并按条目比较时间，取较晚的记录，删除以标记的形式保留在清单里，所以两边各自的增删都不会丢。

### 示例：把副机的改动合并到主力机

假设在副机上装了 `vercel-labs/agent-skills` 里的 `web-design-guidelines`，又删掉了 `smell`。

**1. 副机：正常增删，不提交**

```bash
skillctl add vercel-labs/agent-skills --skill web-design-guidelines
```

```bash
skillctl remove smell
```

**2. 把副机的清单传到主力机**

副机仓库根目录的 `skills.json` 用隔空投送、网盘或 U 盘传到主力机任意位置，文件名不用改。不要直接覆盖主力机仓库里的 `skills.json`，那样主力机上副机没见过的改动会丢，也不会触发安装和卸载。

**3. 主力机：合并**

```bash
skillctl merge ~/Downloads/skills.json
```

skillctl 先列出这次会带来的改动，等你确认：

```text
The merge brings 3 change(s):
  remove smell (smallnest/goal-workflow:skills/smell)
  vercel-labs/agent-skills pinned at 64bee5b
  add web-design-guidelines (vercel-labs/agent-skills:skills/web-design-guidelines)
Merge, then install and uninstall to match? [y/N] y
Installed web-design-guidelines (vercel-labs/agent-skills:skills/web-design-guidelines)
Uninstalled smell
Note: README is out of sync with the manifest; update it on the main Mac (purpose and category are written by hand):
  [global] exists but missing from README: web-design-guidelines, source vercel-labs/agent-skills
  [global] in README but does not exist: smell
```

回答 `y` 之外的任何内容都会取消，清单和本机安装都不变。在脚本里运行时，加 `--yes` 跳过确认。传进来的文件原样保留，确认没问题后可以自己删掉。

**4. 主力机：补 README，提交推送**

```bash
git add skills.json README.md && git commit -m "sync skills from second Mac" && git push
```

**5. 副机：确认已送达**

```bash
skillctl sync
```

```bash
git diff -- skills.json
```

第二条命令没有输出，说明副机的改动已经全部进了主力机。

同一个文件 merge 两次，第二次会显示 `Nothing to merge`；拷来的文件比主力机旧也没关系，较新的记录不会被覆盖。

### gstack 安装

gstack 的 SKILL.md 把 `~/.claude/skills/gstack/bin/...`、`ETHOS.md` 等写成了绝对路径，所以它的路由入口用链接安装：`~/.agents/skills/gstack` 直接软链到 gstack 的仓库副本。选用的几个 skill 加 `gstack-` 前缀复制安装：

```bash
skillctl add garrytan/gstack --skill . --link
```

```bash
skillctl add garrytan/gstack --skill office-hours,plan-ceo-review,plan-eng-review --prefix gstack-
```

| 全局名 | 上游目录 |
|---|---|
| `gstack` | 仓库根目录（链接安装） |
| `gstack-office-hours` | `office-hours/` |
| `gstack-plan-ceo-review` | `plan-ceo-review/` |
| `gstack-plan-eng-review` | `plan-eng-review/` |

- 升级用 `skillctl update garrytan/gstack`，不用 gstack 自带的 `/gstack-upgrade`。
- 链接安装的入口直接指向仓库副本，没有标记文件。仓库副本里已跟踪的文件被改过时，sync 和 update 都不切换版本，只报告，要升级得先还原这些改动。
- `office-hours` 会用到 `browse/dist/browse` 二进制（需 `bun run build`），未编译时代码内有存在性判断和 fallback，只影响网页浏览部分。
- 不要在仓库副本里执行官方 `./setup`，它会一次装上全部 61 个 skill。

---

## License

本仓库代码采用 MIT License（见根目录 `LICENSE`）。

`skills/clarify-thought/` 为第三方 MIT 授权内容，版权归原作者所有，授权文本见该目录下的 `LICENSE`。

`third_party/` 下均为 git submodule，各自遵循其上游仓库的许可协议。
