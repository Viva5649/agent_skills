# `audit-docs-landscape` 设计说明

> 本文面向要修改 `audit-docs-landscape` 的维护者，解释缺口推导、导航检查、输出和设计取舍。运行时行为以 [SKILL.md](../../skills/audit-docs-landscape/SKILL.md) 和 [报告模板](../../skills/audit-docs-landscape/references/report-template.md) 为准；本文是该 Skill 的权威设计说明，不作为安装包的运行依赖。
>
> 单篇文档的可读性审查与写作收尾见 [`optimize-docs-readability` 设计](./optimize-docs-readability-design.md)。两份设计各自维护所属 Skill；共同术语沿用根 `CONTEXT.md`。
>
> **按需要读**：修改 `SKILL.md` 看第 7–11 节和第 14 节；了解取舍与依据看第 12、17 节；查验证记录看第 13 节，查决策出处看第 15 节，查待决问题看第 16 节。第 14.1 节约束设计维护者，第 14.2 节约束 Skill 的运行时行为。

## 1. 一句话定位

`audit-docs-landscape` 回答：**一个真人打开仓库时，该有的文档在不在、能不能被找到？**

Skill 以一个仓库为范围，盘点已有文档，从代码证据推导 Documentation gap，并检查跨篇导航。它产出附证据和落地归属的 findings，保持仓库文件只读，仅创建审查报告及其输出目录。

本文用 **Viewer** 指调用 Skill 并阅读其 findings 的人，用 **Reader** 指已有文档或拟议缺失文档的读者，两者不可互换；完整辨析见第 6 节。

## 2. 要解决的核心问题与背景

Viewer 在 2026-09-03 明确了三个痛点及其重要等级 `#2 > #3 > #1`。编号沿用 Viewer 当时的列举顺序，不表示优先级；下表按重要等级从高到低排列：

| 原始编号 | 痛点 | 归属 |
| --- | --- | --- |
| #2 | 单篇文档本身难读——结构混乱、术语没解释、把教程和参考手册混在一起 | `optimize-docs-readability` |
| #3 | 该有的文档根本不存在——没有架构说明、没有"为什么这么设计"的记录 | `audit-docs-landscape` |
| #1 | 入口和导航——新人不知道该读哪篇、从哪开始，文档之间没有路径 | `audit-docs-landscape` |

生态调研结论（同日）：`#2` 在 skills 生态里是真空，没有可信的文档审查型 Skill；`#3` 和 `#1` 也没有。本机既有 Skill 覆盖的是**撰写**（`codebase-documenter`）、**漂移检测**（`neat-freak`）和**规格逆向**（`spec-miner`），没有任何一个从真人读者视角审查既有文档。

本 Skill 承接痛点 #3 与 #1；痛点 #2 的设计由 [`optimize-docs-readability` 设计](./optimize-docs-readability-design.md) 承载。

## 3. 设计目标

1. 盘点结论必须能追溯到具体 Reader、Purpose 与证据，不从通用文档清单推导缺口。
2. 缺失文档的判据从仓库代码的实际结构推导。
3. 全仓库盘点是低频动作，与高频的逐篇可读性审查分开。
4. 每条 finding 指定既有 Skill 作为落地归属，不留悬空待办。
5. 导航检查区分无入链与入口不可达，声明被追踪 Markdown 的统计限制。
6. 判据由 `SKILL.md` 承载；未证明需要前不引入脚本和测试。

## 4. 明确非目标

本 Skill 不修改被审仓库，不从零撰写文档，不做文档与代码行为的语义一致性对账，不逆向规格或 API 文档，不建立领域词汇表或 ADR。它也不审查单篇文档的措辞、需求或设计方案的正确性，不构建或发布文档站点，不做链接可达性的网络校验。

Agent-directed file、代码注释、docstring 和标识符命名不属于默认盘点对象，范围见第 8 节。

## 5. 与既有 Skill 的边界

| Skill | 它做的 | 与本 Skill 的分界 |
| --- | --- | --- |
| `optimize-docs-readability` | 审查单篇文档的 Reader loss；在写作任务中优化当前长文草稿 | 信息已写下但文内表达让 Reader 自己找回来归它；缺失信息与跨篇导航归本 Skill，详见第 7.1 节与 [`optimize-docs-readability` 设计](./optimize-docs-readability-design.md) |
| `codebase-documenter` | 撰写 README、架构文档、API 文档、注释 | 本 Skill 指出缺口与归属，由它撰写 |
| `neat-freak` | 让文档、规则文件、agent memory 与代码和运行时行为对齐 | 它查语义是否与代码相符；本 Skill 查文档需求是否被满足与入口能否到达 |
| `spec-miner` | 从既有代码逆向出规格、依赖图、API 文档 | 本 Skill 只指出缺口并交给它生产内容 |
| `domain-modeling` | 建立 `CONTEXT.md` 和 `docs/adr/` | 它承接决策理由缺失、ADR 等 finding |
| `ce-doc-review` | 审查需求、计划、spec 和设计方案的正确性、完整性与可行性 | 本 Skill 不判断方案是否成立 |
| `codebase-design` | 让模块对 AI 可导航 | 目标读者不同，本 Skill 优化真人导航；冲突时本 Skill 范围内以真人读者为准 |

## 6. 领域语言

本设计的术语是根 [`CONTEXT.md`](../../CONTEXT.md) 的 topic `Documentation Readability`，不新建 context 文件。

该 topic 定义：Repository documentation、Reader、Purpose、Purpose confusion、Reader-transferred work、Intrinsic difficulty、Reader loss、Documentation gap、Orphan document、Doc landscape、Agent-directed file、两个 Skill 名，以及这两份设计的合称（Documentation Readability design）。术语定义与 `_Avoid_` 别名以 `CONTEXT.md` 为准，本文不重复。

三点属于审查流程细节而非词汇表内容，记在这里：

- 四种 Purpose 取自 Diátaxis：`TUTORIAL`（带着走一遍）、`HOW-TO`（完成一个具体任务）、`REFERENCE`（查一个事实）、`EXPLANATION`（理解为什么）。
- Purpose confusion 之所以是问题，是因为不同 Purpose 的阅读模式相反——`TUTORIAL` 要顺序读，`REFERENCE` 要跳读——混在一篇里两类 Reader 都被拖累。
- **Viewer**：调用这两个 Skill、并阅读其 findings 的人。它不是 `CONTEXT.md` 的术语。与 Reader 必须分清——Reader 是被审查文档的读者，Viewer 是审查输出的读者。

## 7. 判定基础

### 7.1 缺口证据与职责分工

**每条 Documentation gap 必须从具名代码证据推导。** 常见文件名的缺席不足以证明缺口；审查者必须说明哪项代码或项目约定使哪类 Reader 在什么时机需要该文档。

两份设计沿用 Reader-transferred work 原理：文档缺陷是作者把本可以完成的工作转移给 Reader。“Reader 需要思考”本身不构成缺陷；主题本身的 Intrinsic difficulty 也不构成可读性缺陷。完整原理与推导依据见 [`optimize-docs-readability` 设计](./optimize-docs-readability-design.md) 第 7.1 节。

内容问题按信息是否存在分工：作者已有该信息，但文内表达让 Reader 自己找回来，归 `optimize-docs-readability`；理解所需的信息从未被写在任何地方，归本 Skill 的 Documentation gap。跨篇导航始终归本 Skill，包括信息已写下、但从入口找不到的情况。

### 7.2 先判定 Reader 与 Purpose

已有文档和拟议缺口都先确定 Reader 与 Purpose，再做内容判断。README、CONTRIBUTING、架构说明各有不同读者，固定一个画像会使结论脱离实际需求。知识的诅咒解释了审查者为什么不能用自己的知识代替 Reader 的视角，来源见第 17.1 节。

顺序固定为 Reader → Purpose → 内容判断，不可颠倒。

### 7.3 自动推定的证据来源

Viewer 在 2026-09-03 选择自动推定，而不是每篇都问。已有文档的证据按以下顺序取用：

1. 文档自己的声明：标题、前言、“本文面向…”等。
2. 文档在仓库中的位置和文件名。
3. 谁链接到它、用什么措辞链接。
4. 代码实际形态：对外契约或内部机制。

审查者为拟议的缺失文档从具名代码证据与项目约定确定 Reader/Purpose。输出必须列出推定结果和依据，不能只给结论。

### 7.4 证据不足时的处理

审查者报告 Reader 无法判定，停止依赖该推定的内容判断，不得编造画像后继续推导缺口。审查者继续执行有独立证据的探针与链接存在性检查；已有文档和拟议缺口均适用。

## 8. 审查对象范围

### 8.1 在范围内

面向真人的仓库文档：任何层级的 `README`、`docs/` 下的 Markdown、架构说明、onboarding、runbook、ADR、根目录的设计说明文档。

### 8.2 不在范围内

| 排除项 | 理由与处理 |
| --- | --- |
| Agent-directed file | 读者是模型。按读者和指令引用关系判定，不仅匹配 `AGENTS.md`、`CLAUDE.md`、`SKILL.md` 等文件名；被指令文件纳为自身规则的文档也排除，例如根 `AGENTS.md` 引用的 `docs/agents/*`。审查者仍可读取这些文件中的项目约定，作为文档需求的证据；显式要求纳入时，将 Reader 判定为维护指令的人，保留指令语义 |
| 由脚本或模板反复生成的产物 | 修改会被下次生成覆盖。发现 generator 时报告应审查模板或 generator，并停止对该产物的内容判断 |
| 代码内文档 | 注释、docstring、标识符命名不属于 Repository documentation |
| 外部约定格式 | LICENSE、法律声明、Changelog 规范格式、第三方模板的措辞和固定结构不做改写 |
| Intrinsic difficulty | 主题本身难不能用来证明文档缺陷或缺口 |

## 9. 仓库盘点协议

### 9.1 触发与输入

Viewer 要求盘点一个仓库的文档全貌。低频、全仓库范围。

与 `optimize-docs-readability` 的触发歧义处理：Viewer 只提到单篇文档时走 `optimize-docs-readability`，提到"整个仓库""有哪些文档""缺什么"时走 `audit-docs-landscape`。这只是措辞层面的初判。内容问题按第 7.1 节分工：**信息已被写下但文内表达让 Reader 自己找回来属于 `optimize-docs-readability`；信息从未被写在任何地方属于 `audit-docs-landscape`**。跨篇导航由 `audit-docs-landscape` 检查，不受信息是否已写下的限制。`optimize-docs-readability` 在审查中发现某段的问题其实是"这件事整个仓库都没写过"时，不自行补写，把它移交 `audit-docs-landscape`。

`audit-docs-landscape` 建立文档清单时，按第 8.2 节的读者与指令引用关系排除 Agent-directed file。推导缺口前，`audit-docs-landscape` 按第 7.3 节记录已有文档的 Reader、Purpose 和依据；对拟议的缺失文档，从代码形态与项目约定取证。证据不足时，报告无法判定，停止依赖该推定的内容判断，继续有独立证据的探针与链接存在性检查。

### 9.2 缺失推导探针

**核心不变量：缺失判据必须从代码的实际结构推导，不能是通用清单。** 否则退化成"你没有 CONTRIBUTING.md"这种废话。

五条推导路径：

| 探针 | 从什么推导 | 应存在的文档 |
| --- | --- | --- |
| 模块边界 | 顶层模块、服务、包的划分 | 每个的职责边界写在哪 |
| 非显然技术选型 | 依赖清单、配置、构建脚本里不是默认选择的部分 | "为什么选它"的记录（→ ADR） |
| 人工运维动作 | 迁移脚本、密钥轮换、发布流程 | runbook |
| 多运行模式 | dev/prod 分支、feature flag、环境变量矩阵 | 模式差异说明 |
| 对外契约 | HTTP 路由、CLI 命令、公开导出符号 | 参考文档 |

**`audit-docs-landscape` 优先报告不会过期的缺口。** 决策与理由（为什么这样选）长期有效；结构复述（有哪些模块、各自调用谁）会随代码漂移，且读代码本来就能得到。当一条缺失 finding 指向的是结构复述时，`audit-docs-landscape` 降低该条的建议强度，并在这条 finding 里写明这个权衡。

### 9.3 导航与孤岛检查（痛点 #1）

`audit-docs-landscape` 先汇集仓库所有被追踪 Markdown 的链接，再从选定的 README 或入口文档出发遍历。在被追踪 Markdown 范围内，将盘点清单与入口实际到达的文档集合比较，产出四类结论：

- **Orphan document**——存在但没有任何被追踪 Markdown 链接到它。
- **入口不可达**——文档存在，但从选定入口沿链接无法到达；即使它与其他文档互相链接也要报告。此项不改变 Orphan document 的定义；同一文档同时符合两项时合并为一条 finding。
- **入口冲突**——多篇文档都自称是起点。
- **断链**——链接指向不存在的文件或锚点。

选定入口自身没有入链不构成导航缺陷。例：`README → guide`、`a ↔ b` 的所有链接都有效，`audit-docs-landscape` 仍应报告 `a`、`b` 从入口不可达，不把 README 自身列为缺陷。

**已知限制必须在输出中声明**：只统计被追踪 Markdown 文件之间的链接。从代码注释、外部站点、聊天记录指向的文档会被误判为 Orphan。声明这个限制比给一个假装完整的孤岛列表有用。

### 9.4 Finding 格式与排序

输出先列出 Reader/Purpose 判定及证据依据，再给出 findings；证据不足的项明确标为未判定，不用猜测补齐。

| 字段 | 内容 |
| --- | --- |
| 缺口 | 缺失的文档，或具体的导航问题 |
| 代码证据 | 触发它的具体路径。**没有代码证据的条目不报** |
| 谁在什么时候被卡住 | 具体的 Reader 和触发时机（新人第一天、发布当晚、故障排查时） |
| 落地归属 | 指派给 `codebase-documenter`、`domain-modeling`（ADR）或 `spec-miner` |

"落地归属"字段是 `audit-docs-landscape` 在四个既有 Skill 旁边成立的理由：它是派单器，不是抱怨清单。

**与 `optimize-docs-readability` 相反，`audit-docs-landscape` 排序。** 按"谁被卡住、多快被卡住"降序。理由：写一篇新文档昂贵，Viewer 需要知道先写哪篇；而 `optimize-docs-readability` 的改写便宜，分级是浪费。这个不对称是有意的。

**必须报告未产出缺口的探针。** 与可读性审查的判据覆盖报告同理：只交 findings，Viewer 无法区分"探针执行了、没找到缺口"和"探针被静默跳过"。这与第 9.5 节那条不同——那条管的是探针**无法执行**（代码证据读不到），这条管的是探针**执行了但无缺口**。两种都要出现在输出里。

### 9.5 停止条件

- 仓库规模超出一次会话能建立可信模块清单的范围 → 报告实际覆盖到的范围，不假装完整。
- 没有 README 或任何入口文档 → 这本身是头号 finding，导航检查退化为"入口不存在"，不再遍历。
- 探针需要的代码证据读不到（如构建配置缺失）→ 报告该探针未执行及原因，不用通用清单补位。

## 10. 目录与加载

```text
/
├── docs/design/audit-docs-landscape-design.md
└── skills/audit-docs-landscape/
    ├── SKILL.md
    └── references/report-template.md
```

五个缺失探针和四项导航检查由 `SKILL.md` 承载，报告模板单独存放；当前没有 `scripts/`、`tests/`、`evals/`。不引入脚本的理由与提取条件见第 12.2 节。

执行 Skill 的 agent 仅在第 4 步起草报告时加载本 Skill 自带模板，取证阶段不加载；第 5 步复用模板记录证据复核结果，再保存和交付报告。本 Skill 不引用另一 Skill 的报告模板。判据需要成篇的正反例时，再增加对应的参考文件。

## 11. 输出与落盘

完整报告默认保存到被审仓库根目录下的 `.scratch/docs-review/<date>-landscape-<repository>.md`；非 Git 项目使用工作区根目录。执行 Skill 的 agent 根据审查目标确定根目录，不使用 Skill 安装目录或特定电脑的固定路径；输出目录不存在时创建。

`<date>` 使用 `YYYY-MM-DD`，`<repository>` 使用被审仓库根目录的目录名。agent 将名称中的空白和文件名非法字符（`/ \ : * ? " < > |`）替换为连字符。同名文件已存在时，在 `.md` 前依次追加 `-2`、`-3` 等后缀，不覆盖已有报告。

会话内返回简短摘要和报告链接。Viewer 显式指定路径或要求不落盘时按其要求执行；保存失败时，agent 在会话内交付完整报告并说明未保存及原因。除报告及输出目录外，不创建、编辑、移动或删除文件。

### 11.1 保存与交付前的证据复核

审查 agent 在第 4 步完成报告草稿后，于第 5 步做一次基于仓库证据的复核；即使没有 findings，也必须复核覆盖情况。不默认增加第二个 reviewer。

1. 对每个拟议缺口搜索仓库内其他名称或位置的已有内容，确认具名代码证据确实产生该 Reader 的文档需求。
2. 用被追踪 Markdown 链接和选定入口复现每条导航结论，保留入口豁免，并合并同一文档的 Orphan 与入口不可达发现。
3. 核对五个探针、四项导航检查及实际覆盖范围，区分无发现与无法执行。

agent 删除误报、修正证据不足的结论，并对修正后的 finding 核对证据。无法核实的结论移入未验证项，不作为已确认 finding。agent 在模板中记录复核方式、核对的证据、修正摘要（或无修正）及未验证项，再保存交付。此环节是同一 agent 的证据自查，不冒充独立复核，也不保证没有遗漏。

## 12. 关键取舍

### 12.1 Skill 与设计文档各自分开

Viewer 在 2026-09-03 选择拆分。逐篇审查是高频、范围小、可以只对改动过的文档跑；全仓库盘点是低频、范围大。合成一个会导致每次改一篇 README 都触发全仓库扫描。原设计为保持共同基础一致，合并为一份设计文档。2026-10-02 按 Viewer 要求调整为一个 Skill 对应一份 design；维护者修改共同原则或职责边界时，需核对另一份设计，避免两边冲突。

### 12.2 第一版不写脚本

本仓库既有的 `write-implementation-tickets`、`execute-tickets` 两个 Skill 都是脚本承载确定性逻辑、`SKILL.md` 承载判断。`optimize-docs-readability` 与 `audit-docs-landscape` 里唯一确定性可计算的部分是第 9.3 节的链接图遍历。但它服务的是 Viewer 排在最末的痛点 `#1`；为最低优先级的功能先付脚本加测试的成本不成比例。

第一版用 Grep 做链接遍历。**提取脚本的触发条件**：被审仓库文档数超过约 30 篇导致人工遍历不可靠，或 Viewer 报告 Orphan 判定出现漏报。届时脚本只负责计算链接图与孤岛，不做任何"这篇该不该存在"的判断。

### 12.3 自动推定读者而不是每篇都问

Viewer 在 2026-09-03 选择自动推定。逐篇确认读者会把一次审查变成一轮问答，抵消掉 Skill 的价值。代价是推定可能出错，因此第 7.3 节要求列出推定依据、第 7.4 节禁止无证据推测——把出错变成可见且可纠正的，而不是隐藏在 findings 背后。

### 12.4 排除 Agent-directed file

Viewer 的原始诉求是"对真人可读"。`AGENTS.md`、`SKILL.md` 这类文件的读者是模型，判据不同甚至相反。若纳入，Skill 会用真人阅读标准"优化"这些文件的措辞，直接损害 agent 表现。代价是这些文件的人类维护者拿不到审查——需要时显式要求，且此时 Reader 判定为维护者。

### 12.5 缺口与导航 finding 排序

不对称是有意的，依据是修复成本：改一句话便宜，写一篇文档昂贵。分级只在修复成本高到需要排序时才值得维护。

## 13. Verification strategy

Viewer 在 2026-09-03 选择先不做评测、直接使用。以下区分拟议的人工验证与已经执行的历史核对，不将确定性检查当作真实仓库效果评测。

### 13.1 首轮人工验证

| 对象 | 验证什么 |
| --- | --- |
| 全仓库跑 `audit-docs-landscape` | 当时根目录仍无 README，但已新增 `docs/README.md`，面向要修改 Skill 的维护者，指向 `docs/design/` 与 `docs/agents/`。先判定它能否作为全仓库入口，再判断是否进入第 9.5 节的入口不存在分支；这是该分支的边界样本 |
| `docs/agents/*` | 原合并设计的可读性自审已暴露按文件名排除的缺陷：根 `AGENTS.md` 引用这些文件作为自身规则，读者是模型。两份 Skill 的排除规则均需按读者和指令引用关系执行，见第 8.2 节 |

### 13.2 判据是否成立的判定标准

两道关卡，顺序固定：

1. 派生测试：判据必须能写成“Reader 被迫做 X，而作者本可以做掉 X”。缺失 finding 同时必须指名产生文档需求的代码证据，不能来自通用清单。
2. 经验测试：判据至少产出一条 Viewer 认可的 finding，且没有产出成批误报。过了派生测试却在经验测试失败时，先检查执行是否偏离原理、判据是否过宽，再决定改措辞或删除。只产生误报的判据不靠调参保留。

Viewer 通过报告中无缺口的探针与无法执行项，判断各项检查是否真的执行；只看 findings 无法证明覆盖。

### 13.3 引入评测的触发条件

出现以下任一情况时，按 `skill-creator` 的评测流程补 eval：

- 同一条判据在不同仓库上表现相反，无法靠读 `SKILL.md` 判断哪次是对的。
- 修改判据措辞后无法确认是改好了还是改坏了。
- 第 7.4 节的无证据禁令被违反，findings 建立在虚构 Reader 上。
- 第 8.2 节的 Intrinsic difficulty 排除失效，主题本身难被当作文档缺陷。

### 13.4 2026-09-07 修正验证

| 对象 | 已执行的核对及结果 |
| --- | --- |
| 导航规则 | 对 `README → guide`、`a ↔ b` 和一个无入链文档做内存图遍历：两个互链文档均不可达；无入链文档同时符合 Orphan 与不可达，合并报告；入口自身无入链不报缺陷。后续修改导航规则时复核这组反例 |
| 指令与设计 | 静态核对读者取证、指令引用排除、导航可达性和按审查目标分工；不将可读性审查当作方案正确性验证 |
| Skill 格式 | `audit-docs-landscape` 通过 `skill-creator` 的 `quick_validate.py`；同时修正 description 中冒号需要 YAML 引号的问题 |

以上不代表完成真实仓库的 Skill 效果评测。首轮人工验证仍按第 13.1 节列出的证据需求进行。

## 14. 修改本设计时必须保持的不变量

### 14.1 约束修改本设计的人

1. 缺口判据从具名代码证据与 Reader 的需求推导，不用通用清单替代。
2. 判据保留 Reader-transferred work 原理与派生测试，不能把“Reader 需要思考”直接当作缺陷。
3. 判据由 `SKILL.md` 承载；未证明需要前不引入脚本，提取条件见第 12.2 节。
4. 维护共同原则或职责边界时，核对 `optimize-docs-readability` 的设计，保持分工一致。

### 14.2 约束 Skill 的运行时行为

1. 信息已写下但文内表达让 Reader 自己找回来归 `optimize-docs-readability`；从未写下的信息归本 Skill。跨篇导航始终归本 Skill，包括已有文档从入口不可达的情况。
2. Reader/Purpose 判定先于内容判断，且必须有第 7.3 节的证据。证据不足时报告未判定，停止依赖该推定的判断，继续有独立证据的检查。
3. 独立审阅为 review-only：仅允许按第 11 节创建审查报告及输出目录，不改被审仓库。
4. 每条缺失 finding 指名代码证据，说明具体 Reader 在何时被卡住，指定落地归属；无证据的通用清单项不报。
5. Agent-directed file 默认排除；按读者与指令引用关系分类，显式纳入时 Reader 为维护者，并保留指令语义。
6. 生成产物的内容判断应转向 generator 或模板；代码内文档、法律措辞与外部固定格式不做可读性改写。
7. Intrinsic difficulty 不是缺陷。
8. findings 按被卡住的代价排序；与可读性 findings 不分级的不对称由修复成本决定，不统一。
9. Orphan 与入口不可达分别判定，同一文档符合两项时合并；入口自身无入链不报缺陷，报告被追踪 Markdown 的统计限制。
10. 输出必须报告无缺口探针、无法执行项及原因，并核对五个探针、四项导航检查和实际覆盖范围。
11. 本 Skill 不从零撰文、不逆向规格、不做文档与代码的漂移对账；证据自查不冒充独立复核。

## 15. 决策来源

| 决策 | 日期 | 内容 |
| --- | --- | --- |
| 痛点优先级 | 2026-09-03 | `#2 > #3 > #1` |
| Skill 拆分 | 2026-09-03 | 拆成两个 |
| 读者判定方式 | 2026-09-03 | 自动推定 |
| 评测时机 | 2026-09-03 | 先不评测，直接用 |
| Review-only | 2026-09-03 | 出缺口与导航 findings，指定落地归属，不改仓库文件 |
| 命名候选 | 2026-09-03 | `docs-coverage-audit` 被否决——coverage 易联想测试覆盖率，且盖不住导航检查 |
| 命名形式 | 2026-09-03 | Skill 名用动词原形，不用 `-ing`：`review-docs-readability`、`audit-docs-landscape`。与本仓库既有 `write-implementation-tickets`、`execute-tickets` 一致 |
| 领域语言归属 | 2026-09-03 | 不新建 context 文件，术语作为一个 topic 加入根 `CONTEXT.md`。当时与它并列的 `Requirement Progress Monitoring` topic 已随 spec-monitor 一并删除，该文件现在只有本设计这一个 topic |
| 分发 | 2026-09-03 | 两个 Skill 落盘后如何分发到 agent 目录由 Viewer 自己处理，不在本设计范围内 |
| 理论依据 | 2026-09-03 | 原合并设计采纳 Reader-transferred work 与 Intrinsic difficulty 排除；本 Skill 以代码证据推导缺口，并据此与可读性审查划分职责 |
| 审查修正 | 2026-09-07 | Viewer 确认：`audit-docs-landscape` 增加入口不可达检查，保留 Orphan 定义，补齐读者取证与指令引用排除；可读性审查的相关修正记录见其设计 |
| 设计文档拆分 | 2026-10-02 | Viewer 要求一个 Skill 对应一个 design；将原合并设计按职责拆为两份，保留各自判据、历史验证及决策依据 |

## 16. 待决问题

1. **`audit-docs-landscape` 在超大仓库的分批策略。** 第 9.5 节目前只要求"报告实际覆盖范围"，没有定义按模块分批的协议。等真实遇到超限仓库后再设计，避免先写一套没有需求验证的分批规则。

## 17. 主要来源索引

### 17.1 理论与 Skill 规则的对应

下表区分来源提供的依据与本设计制定的工程规则。理论没有规定具体探针、导航算法、阈值或报告格式，规则有效性仍需第 13 节的验证。

| 理论来源与依据 | 支撑的具体细节 | 本设计的推导边界 |
| --- | --- | --- |
| Pinker [《The Sense of Style》](https://stevenpinker.com/publications/sense-style-thinking-persons-guide-writing-21st-century)，知识的诅咒（概念源自 [Camerer/Loewenstein/Weber](https://doi.org/10.1086/261651)）：掌握知识的人难以还原不掌握该知识者的视角 | 第 1 步记录已有文档的 Reader/Purpose，第 2 步为拟议缺口确定 Reader/Purpose，第 4 步写明谁在何时被卡住（第 9.1、9.2、9.4 节） | 将 Reader 视角应用于缺口审计是本设计的延伸；具名代码证据与五个探针来自本设计，不是理论给出的文档清单 |
| Procida [Diátaxis](https://diataxis.fr/start-here/)：按用户需要区分 tutorial、how-to、reference、explanation | 第 1、2 步为已有文档和拟议缺口标注四种 Purpose，第 4 步将分类及依据写进盘点表（第 6、9.1、9.4 节） | 四种 Purpose 不是每个仓库必须各有一篇的配额；缺口仍需代码证据，四项导航检查也不是 Diátaxis 的规则 |

五个缺失探针、四项导航检查、报告模板、落盘命名和渐进式加载都是工程规则，上表不为它们主张直接的理论出处。

### 17.2 Skill 与仓库规则来源

| 来源 | 作用 |
| --- | --- |
| `github/awesome-copilot@documentation-writer` | 接触 Diátaxis 四种 Purpose 分类的参照入口。其流程是 Clarify → Propose Structure → Generate，纯生成无审查路径，因此只借分类判据，不借流程 |
| [`CONTEXT.md`](../../CONTEXT.md) | 本设计术语的权威定义及禁止混用的别名 |
| [`optimize-docs-readability-design.md`](./optimize-docs-readability-design.md) | Reader-transferred work 原理的完整论证、单篇可读性审查及双方职责分工 |
