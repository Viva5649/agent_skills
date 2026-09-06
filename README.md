# agent_skills

个人 Agent Skill 仓库。收录自建 skill，并以 git submodule 方式聚合常用的外部 skill 库。

本文档记录本机（macOS）当前的 skill 全貌，分三层：仓库自建、全局安装、项目级。来源仓库取自各 skill 目录下的 `.openskills.json`。

- 自建 skill：8 个（`skills/`）
- 全局安装：39 个（`~/.claude/skills/`）
- 项目级：6 个（`personal_ai_infrastructure/.claude/skills/`）
- 外部聚合：7 个仓库，共 200 个 skill（`third_party/`）

---

## 一、仓库自建 skill（`skills/`）

| Skill | 用途 | 源仓库 | 全局已装 |
|---|---|---|:---:|
| `clarify-life-direction` | 人生方向澄清。回溯经历、澄清愿景、定义反愿景、倒推路径，把「不知道自己想要什么」变成可执行方向 | [Viva5649/agent_skills](https://github.com/Viva5649/agent_skills) | ✅ |
| `clarify-thought` | 命题分解与决策澄清。维特根斯坦 + 苏格拉底 + 波兰尼三层架构，把模糊想法拆成精准指令或清晰决策 | [Viva5649/clarify-skill](https://github.com/Viva5649/clarify-skill)（原作者 riiiku） | ✅ |
| `create-blueprint` | 生成工程蓝图风格技术图表，支持箭头、连线、关系标注，用于架构图与流程图 | [Viva5649/agent_skills](https://github.com/Viva5649/agent_skills) | ✅ |
| `creator-signal-digest` | 创作者信号雷达周报。扫描中文圈/英语圈 AI 创作者账号，筛选 AI 实操与副业信号 | [Viva5649/agent_skills](https://github.com/Viva5649/agent_skills) | ❌ |
| `explain-concept` | 概念通俗讲解与可视化。输出生活化例子、记忆方法，适合时按概念结构选 mermaid / SVG / HTML 出图 | [Viva5649/agent_skills](https://github.com/Viva5649/agent_skills) | ❌ |
| `optimize-prompt` | 提示词优化。基于 57 个提示词框架选择合适结构，先澄清目标、受众、上下文再改写 | [Viva5649/agent_skills](https://github.com/Viva5649/agent_skills) | ✅ |
| `publish-site` | 管理个人 Vantage 站点，把已准备好的内容转成双主题编辑风格 HTML 报告并发布 | [Viva5649/agent_skills](https://github.com/Viva5649/agent_skills) | ✅ |
| `send-email` | 通过 SMTP 发送邮件，支持 Markdown 转 HTML、附件、多收件人与 CC/BCC | [Viva5649/agent_skills](https://github.com/Viva5649/agent_skills) | ✅ |

> `clarify-thought` 迁移自独立仓库 `Viva5649/clarify-skill`，原作者 riiiku（MIT，署名保留在 `skills/clarify-thought/LICENSE`）。

---

## 二、全局安装 skill（`~/.claude/skills/`）

对所有项目生效，由 [openskills](https://github.com/vercel-labs/skills) 安装。

「`third_party/` 收录」列说明这个 skill 的**上游仓库**在本仓库里能不能直接翻到源码：

- ✅ 上游仓库已作为 submodule 收进 `third_party/`，`cd third_party/xxx` 就能看源码、查历史、跟版本
- ❌ 上游仓库还没收进来，只有装到 `~/.claude/skills/` 的那一份，想看源码得去 GitHub，清单见「四」的「尚未聚合的上游仓库」
- 本仓库 该 skill 是自建的，正文在 `skills/` 下，没有外部上游

### 官方 / Anthropic

| Skill | 用途 | 源仓库 | `third_party/` 收录 |
|---|---|---|:---:|
| `docx` | Word 文档（.docx/.dotx）创建、读取、编辑，含目录、页眉、修订与批注 | [anthropics/skills](https://github.com/anthropics/skills) | ✅ |
| `pdf` | PDF 读取、合并、拆分、加水印、填表单、加解密、OCR | [anthropics/skills](https://github.com/anthropics/skills) | ✅ |
| `pptx` | PPT（.pptx/.potx）创建、解析、编辑，含模板、版式、演讲者备注 | [anthropics/skills](https://github.com/anthropics/skills) | ✅ |
| `xlsx` | 电子表格（.xlsx/.csv/.tsv）创建、编辑、公式、图表、脏数据清洗 | [anthropics/skills](https://github.com/anthropics/skills) | ✅ |
| `frontend-design` | 前端视觉设计指导，审美方向、排版、避免模板化默认样式 | [anthropics/skills](https://github.com/anthropics/skills) | ✅ |
| `skill-creator` | 创建、修改、优化 skill，跑 eval 测试与描述调优 | [anthropics/skills](https://github.com/anthropics/skills) | ✅ |

### 工程 / 方法论

| Skill | 用途 | 源仓库 | `third_party/` 收录 |
|---|---|---|:---:|
| `brainstorming` | 任何创作性工作前的强制前置，先探清意图、需求与设计再动手 | [obra/superpowers](https://github.com/obra/superpowers) | ✅ |
| `writing-plans` | 有 spec 或需求的多步任务，先写计划再碰代码 | [obra/superpowers](https://github.com/obra/superpowers) | ✅ |
| `agent-browser` | 浏览器自动化 CLI，导航、填表、截图、抓数据、测试 Web 与 Electron 应用 | [vercel-labs/agent-browser](https://github.com/vercel-labs/agent-browser) | ❌ |
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
| `khazix-writer` | 数字生命卡兹克风格的公众号长文写作，支持素材转长文、续写、扩写 | [KKKKhazix/khazix-skills](https://github.com/KKKKhazix/khazix-skills) | ✅ |
| `humanizer` | 改写 AI 腔文本，去除套话、虚高措辞、重复结构，保持原意不变 | [blader/humanizer](https://github.com/blader/humanizer) | ❌ |
| `guizang-ppt-skill` | 横向翻页网页 PPT（单 HTML），含 WebGL 背景与演讲者视图，两种风格 | [op7418/guizang-ppt-skill](https://github.com/op7418/guizang-ppt-skill) | ❌ |
| `huashu-design` | HTML 高保真原型、幻灯片、动画、可视化，新设计强制先出三稿供选 | [alchaincyf/huashu-design](https://github.com/alchaincyf/huashu-design) | ❌ |
| `baoyu-article-illustrator` | 文章配图。分析结构定位需要插图的位置，按类型 × 风格 × 配色三维生成 | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) | ✅ |
| `baoyu-cover-image` | 文章封面图。类型、配色、渲染、文字、情绪五维组合，支持 2.35:1 / 16:9 / 1:1 | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) | ✅ |
| `create-blueprint` | 工程蓝图风格技术图表 | [Viva5649/agent_skills](https://github.com/Viva5649/agent_skills) | 本仓库 |
| `publish-site` | Vantage 站点报告发布 | [Viva5649/agent_skills](https://github.com/Viva5649/agent_skills) | 本仓库 |

### 个人决策 / 思考

| Skill | 用途 | 源仓库 | `third_party/` 收录 |
|---|---|---|:---:|
| `clarify-thought` | 命题分解与决策澄清 | [Viva5649/clarify-skill](https://github.com/Viva5649/clarify-skill) | 本仓库 |
| `clarify-life-direction` | 人生方向澄清 | [Viva5649/agent_skills](https://github.com/Viva5649/agent_skills) | 本仓库 |
| `optimize-prompt` | 提示词优化 | [Viva5649/agent_skills](https://github.com/Viva5649/agent_skills) | 本仓库 |

### Skill 管理自身

| Skill | 用途 | 源仓库 | `third_party/` 收录 |
|---|---|---|:---:|
| `skill-manager` | GitHub 来源 skill 的生命周期管理，批量扫描、检查更新、引导升级 | [KKKKhazix/Khazix-Skills](https://github.com/KKKKhazix/Khazix-Skills) | ✅ |
| `skill-evolution-manager` | 会话结束时根据反馈迭代已有 skill，把对话精华固化回 skill 库 | [KKKKhazix/Khazix-Skills](https://github.com/KKKKhazix/Khazix-Skills) | ✅ |
| `github-to-skills` | 把 GitHub 仓库自动打包成 skill，抓取仓库信息与最新 commit 生成标准结构 | [KKKKhazix/Khazix-Skills](https://github.com/KKKKhazix/Khazix-Skills) | ✅ |
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

> 上游共 61 个 skill，这里只装了需要的几个，装法见「五、状态说明」的 gstack 小节。

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

> 注：`KKKKhazix/Khazix-Skills` 与 `KKKKhazix/khazix-skills` 是同一仓库的不同大小写写法，`skill-manager`、`skill-evolution-manager`、`github-to-skills` 三个 skill 位于该仓库但不在其 `skills/` 目录下。

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
| 全局与 `third_party/` 内容重复 | 预期行为，非问题。`third_party/` 的定位是集中管理与查阅上游仓库，全局 skill 由 [openskills](https://github.com/vercel-labs/skills) 工具独立安装，两者各司其职 |

### gstack 安装（选择性安装，不走官方 setup）

gstack 既不走 openskills，也没有用它自带的 `./setup`。官方脚本会一次性安装全部 61 个 skill，且要求 gstack 位于 `~/.claude/skills/gstack`（脚本把 skill 装到 gstack 目录的**父目录**下）。这里只需要其中几个，所以改用仓库自带的 [`scripts/link-gstack-skills.sh`](scripts/link-gstack-skills.sh) 从 `third_party/gstack` 选择性链接。

脚本同时处理 `~/.claude/skills/`（Claude Code）和 `~/.agents/skills/`（其他 agent）。后者只在已存在时处理，本机没有这套约定就跳过，不主动创建。

```bash
./scripts/link-gstack-skills.sh --prune
```

想要哪些 skill，改脚本顶部的 `WANTED` 数组即可。当前安装：

| 全局名 | 上游目录 |
|---|---|
| `gstack` | `third_party/gstack`（路由 skill，入口软链顺带注册） |
| `gstack-office-hours` | `office-hours/` |
| `gstack-plan-ceo-review` | `plan-ceo-review/` |
| `gstack-plan-eng-review` | `plan-eng-review/` |

**脚本做了什么**

1. 在每个目标 skill 目录下建软链 `gstack` 指向 `third_party/gstack`。三个 SKILL.md 把 `~/.claude/skills/gstack/bin/...` 和 `ETHOS.md` 写成了绝对路径，这个软链让它们解析得到，磁盘上仍然只有 submodule 一份。
2. 为每个 skill 建**真实目录**（不是目录软链），内部放指向源文件的软链，且指向本目录自己的 `gstack` 入口，两棵树互不依赖。Claude Code 只扫 `<skills 目录>/<名字>/SKILL.md` 这一层，不递归，整个目录软链过去会扫不到。
3. `SKILL.md` 之外的同级资源全部链过去，排除 `node_modules|dist|test|*.tmpl`。这一步对齐官方 `setup` 的 `_link_skill_runtime_assets`，上游给某个 skill 新增 `references/`、`templates/` 等目录时重跑即可自动跟上。
4. 结尾做断链自检，入口软链自身也在检查范围内。它一断，三个包装目录会跟着全断，而包装目录本身看起来还是好的，所以必须单独查。

**升级**

```bash
git submodule update --remote -- third_party/gstack && ./scripts/link-gstack-skills.sh
```

脚本幂等，重跑安全。上游删除或改名的 skill 会打印提示而不是静默失败。

**注意**

- 该方案绕开了 gstack 自带的 `/gstack-upgrade` 升级机制，版本由 submodule 指针决定。
- 四个 skill 的可用性绑定在 agent_skills 仓库的当前路径上。移动或重命名本仓库后需重跑脚本，它会检测到软链失效并自动刷新。
- `office-hours` 会用到 `browse/dist/browse` 二进制（需 `bun run build`），未编译时代码内有存在性判断和 fallback，只影响网页浏览部分。
- 不要在 `third_party/gstack` 里执行官方 `./setup`，否则 skill 会被装到 `third_party/` 下而不是 `~/.claude/skills/`。

---

## License

本仓库代码采用 MIT License（见根目录 `LICENSE`）。

`skills/clarify-thought/` 为第三方 MIT 授权内容，版权归原作者所有，授权文本见该目录下的 `LICENSE`。

`third_party/` 下均为 git submodule，各自遵循其上游仓库的许可协议。
