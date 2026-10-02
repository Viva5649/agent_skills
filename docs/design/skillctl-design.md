# `skillctl` 设计说明

> 本文说明 skillctl 为什么这样设计，以及各命令的具体规则。设计原则以 [README「设计原则」](../../README.md#设计原则)为准，本文是这些原则的展开；两边不一致时以 README 为准，再回头修正本文。日常用法见 README 第六节，行为由 `scripts/test_skillctl.py` 覆盖。

## 目标

在两台 Mac 上统一管理从 GitHub 拉取的 skill：

- 从 GitHub 仓库按需挑选 skill 安装，并能定期更新；
- 同一个 skill 在 Claude Code、Codex 里是同一份内容、同一个名字；
- 重名在安装时被拦下，需要时用别名让两个 skill 共存；
- 装哪些 skill 记在 agent_skills 仓库的清单里，新电脑 clone 仓库后一条命令装齐；
- 任意一台 Mac 上的增删都能同步到另一台：主力机经 GitHub 分发，副机拷一个文件传回。

## 需求

| 编号 | 需求 |
|---|---|
| R1 | skill 必须跨 Agent 生效，不用 Claude Code plugin |
| R2 | 从 GitHub 拉取；多 skill 仓库可以只装其中几个；可以定期更新 |
| R3 | 重名的 skill 能区分开 |
| R4 | 两台 Mac 都要装 skill；副机能从 GitHub 拉取但不能推送；两台之间能同步少量配置文件 |
| R5 | 副机只增删第三方 skill，不改 agent_skills 里自建 skill 的正文 |
| R6 | 任意一台的增删都要同步到另一台 |
| R7 | 清单只维护 agent_skills 仓库里的一份；新电脑 clone 后能直接装齐；从 git 能看到通过工具改了哪些 skill |
| R8 | 两台装同一版本；仓库副本用浅 clone；`third_party/` 只用来看源码，不参与安装 |
| R9 | 副机上独立维护、不进清单的 skill 不受同步影响，也不会被写进清单；sync 结束时列出它们 |

## 为什么自建

以下判断来自 2026-09 的评估。

- **`npx skills`（v1.7.0）不满足 R3。** 安装目录名直接取 frontmatter 的 `name`，安装前先删掉同名目录再写入，只在汇总里提示一行 `overwrites:`；锁文件以名字为 key；没有改名参数。相关问题 [vercel-labs/skills#1802](https://github.com/vercel-labs/skills/issues/1802)、[vercel-labs/skills#1906](https://github.com/vercel-labs/skills/issues/1906) 未解决，重名保护的实现 [vercel-labs/skills#898](https://github.com/vercel-labs/skills/pull/898) 被关闭，没有合并。
- **fork `npx skills` 的维护成本高。** 要改的 `add.ts`、`update.ts`、`skill-lock.ts` 正是上游改得最频繁的文件：评估前三个月上游共 182 次提交，其中 `add.ts` 就改了 32 次。上游也没有接受这类改动的迹象，fork 会长期分叉。
- **fork openskills 也不划算。** 它没有清单，不保留仓库副本，只写一个安装目录（全局是 `~/.claude/skills`，或者单数的 `~/.agent/skills`，Codex 不读后者），update 时直接覆盖。需要的能力几乎都得重写，能复用的只有命令行骨架和交互勾选。它还依赖 Node 构建，副机分发比单文件 Python 麻烦。
- **Claude Code plugin 不满足 R1。**
- **自建工具只做需要的事。** 单个 Python 文件，只依赖 git 和标准库。Mac 上的 git 来自命令行工具，同一套工具自带 `/usr/bin/python3`，两台都不用额外安装。

## 总体结构

```text
                 GitHub（只读拉取）
                        │ git clone --depth 1 / fetch
                        ▼
  ~/.local/share/agent-skills/repos/<owner>/<repo>    仓库副本，浅 clone，停在清单记录的提交
                        │ 复制；需要时改写 name
                        ▼
  ~/.agents/skills/<安装名>/                          skill 实体，Codex 读取
                        ▲ 软链接
  ~/.claude/skills/<安装名>                           Claude Code 读取

  <工作 clone>/skills.json                             清单，随 agent_skills 仓库分发
```

清单在两台 Mac 之间按两个方向流动：

- **主力机到副机、新电脑**：清单和工具都在 agent_skills 仓库。主力机提交并推送，其他机器运行 `skillctl sync` 时拉取。
- **副机到主力机**：副机上的增删只改它自己 clone 里的清单，不提交。你把这个文件拷到主力机，运行 `skillctl merge`，再由主力机提交推送。

## 名词

| 名词 | 含义 |
|---|---|
| skill 标识 | `owner/repo:仓库内路径`，例如 `anthropics/skills:skills/docx`；位于仓库根目录的 skill，路径写 `.`。标识在两台 Mac 上相同，且始终不变 |
| 安装名 | skill 的目录名，同时也是 SKILL.md 里的 `name:`，Agent 看到和调用的都是这个名字 |
| 工作 clone | 你 clone 到本机的 agent_skills 仓库，`skillctl.py` 和清单都在里面。主力机上是 `~/Desktop/OpenSource/agent_skills`，其他机器放在哪里都可以 |
| 清单 | 工作 clone 根目录的 `skills.json`，记录要装哪些 skill、叫什么名字，以及每个上游仓库用哪个提交。每台机器用的都是自己工作 clone 里的那一份 |
| 仓库副本 | 工具浅 clone 到本机的上游仓库，只含清单记录的那个提交，每台各自维护。agent_skills 自己也有一份仓库副本，用来安装自建 skill，和工作 clone 分开，所以主力机上还没推送的改动不会被装进全局目录 |
| 仓库版本 | 清单 `repos` 里记录的某个上游仓库的提交号。两台都按它安装，只有 update 和新仓库的第一次 add 会写它 |
| 托管 skill | 由 skillctl 安装、目录内带标记文件 `.skillctl.json` 的 skill，以及链接安装的 skill |
| 未托管 skill | 两个全局目录里不归 skillctl 管的 skill，例如副机上自己维护的 skill。skillctl 不改动、不写进清单，只在 sync 和 list 结束时列出 |
| 链接安装 | 不复制文件，而是把仓库副本的根目录直接软链成 skill 目录。只用于正文里写死了自身路径的仓库，目前只有 gstack |

## 文件布局

| 路径 | 内容 | 两台之间怎么同步 | 写入者 |
|---|---|---|---|
| `<工作 clone>/skills.json` | 清单 | 主力机经 GitHub 分发；副机拷文件传回 | skillctl |
| `<工作 clone>/scripts/skillctl.py` | 工具本身 | 经 GitHub 单向分发 | 主力机 |
| `~/.local/share/agent-skills/repos/` | 仓库副本 | 不同步 | skillctl |
| `~/.agents/skills/<安装名>/` | skill 实体和标记文件 `.skillctl.json` | 不同步 | skillctl |
| `~/.claude/skills/<安装名>` | 指向上一行目录的软链接 | 不同步 | skillctl |
| `~/.local/bin/skillctl` | 指向工作 clone 里 `skillctl.py` 的软链接 | 不同步 | skillctl 首次运行时自动创建 |

skillctl 解析自身的真实路径来找到工作 clone，所以 `~/.local/bin/skillctl` 必须指向工作 clone 里的那个 `skillctl.py`。

每次运行 `skillctl.py` 时，都会检查这个软链接：

- 不存在：创建它，指向正在运行的 `skillctl.py`，并打印一行提示；
- 已经指向正在运行的 `skillctl.py`：不做任何事；
- 被其他文件占用，或者指向别处：只提示，不覆盖；
- `~/.local/bin` 不在 PATH 里：额外提示你把它加进 PATH。

## 清单格式

```json
{
  "version": 1,
  "skills": {
    "anthropics/skills:skills/docx": {
      "name": "docx",
      "state": "present",
      "updated_at": "2026-09-26T16:00:00+08:00"
    },
    "garrytan/gstack:.": {
      "name": "gstack",
      "state": "present",
      "link": true,
      "updated_at": "2026-09-26T16:00:00+08:00"
    },
    "garrytan/gstack:office-hours": {
      "name": "gstack-office-hours",
      "state": "present",
      "updated_at": "2026-09-26T16:00:00+08:00"
    }
  },
  "repos": {
    "anthropics/skills": {
      "commit": "3337550…（完整 40 位）",
      "updated_at": "2026-09-26T16:00:00+08:00"
    }
  }
}
```

- `state`：`present` 表示要装，`removed` 表示已删除。删除时不抹掉记录，而是改成 `removed`，这样另一台才知道要删，合并时也能判断两边操作的先后。
- `updated_at`：这条记录最后一次被 add、remove 或改名的时间，固定用 UTC+8，精确到秒。合并时只看这个字段，按时刻比较先后，不按字符串比较。
- **删除记录一直保留**：`removed` 条目不会自动清理。清掉它，另一台还留着的旧 `present` 记录就会在合并时把 skill 装回来。每条只占几行，重新 add 同一个 skill 时这条记录会直接改回 `present`。
- `link`：只有链接安装的条目才有，值为 `true`。
- `repos`：每个上游仓库的版本。`updated_at` 是这条记录最后一次被 add 或 update 写入的时间，合并方式和 skill 条目相同。没有 `repos` 的旧格式清单，sync 时按仓库副本当前的提交补记，不会顺带升级。
- **固定写出格式**：键按字母排序，两个空格缩进，文件以换行结尾。两台合并出相同的内容时，写出的文件逐字节相同，`git diff` 才能准确反映差异。
- **不要手工编辑**：清单只通过命令修改，否则时间戳就不可靠了。

## 命令

| 命令 | 作用 | 会写入什么 |
|---|---|---|
| `skillctl add <owner/repo>` | 交互勾选并安装，流程见下文"交互勾选" | 清单、仓库副本、安装目录 |
| `skillctl add <owner/repo> --skill a,b [--as 名字 \| --prefix 前缀] [--link]` | 非交互安装，按 name 或路径指定，供脚本和 Agent 调用。`--as` 只能用于单个 skill；`--prefix` 给这次新装的所有 skill 统一加前缀，规则见"命名与冲突规则"。对清单里已有的标识再次执行 add 并带上 `--as`，就是改名 | 清单、仓库副本、安装目录 |
| `skillctl remove <安装名>` | 把对应条目标记为 `removed`，并从本机卸载 | 清单、安装目录 |
| `skillctl sync` | 先拉取工作 clone 并合并清单，再把仓库副本切到清单记录的版本，让本机的安装状态与清单一致，最后列出未托管的 skill | 清单、工作 clone、仓库副本、安装目录 |
| `skillctl merge <文件> [--yes]` | 把另一台的清单逐条合并进本机清单，先列出有变化的条目并等你确认，再执行 sync 的安装步骤 | 清单、仓库副本、安装目录 |
| `skillctl update [<owner/repo>]` | 拉取上游最新提交，列出有变化的 skill 和改动的文件，重装它们，并把新版本记进清单 | 清单、仓库副本、安装目录 |
| `skillctl list` | 列出托管 skill 的安装名、标识、提交号和状态；再列出两个全局目录里未托管的 skill，能从 `.openskills.json` 查到来源的给出纳入管理的 add 命令。sync 不会把这些 skill 自动写进清单 | 不写入 |
| `skillctl check` | 只读检查（见"检查"一节），发现问题时退出码为 1 | 只通过 fetch 更新工作 clone 的远端引用；上游有没有更新用 `git ls-remote` 查询，agent_skills 自己用工作 clone 比较 |

`add`、`remove`、`update`、`merge` 在执行前都会先做一次完整的 `sync`，所以无论在哪台 Mac 上使用 skillctl，都会先把仓库里的最新清单带过来。add、remove 和有改动的 merge 完成后，会运行仓库自带的 README 校验，有漂移就提醒你补 README；README 里的用途和分类要人工写，工具不自动改。

### 交互勾选

`skillctl add <owner/repo>` 不带 `--skill` 时，按以下步骤进行：

1. 准备仓库副本，版本规则见下文。然后找出副本里所有包含 SKILL.md 的目录，包括根目录，跳过 `.git` 和 `node_modules`。
2. 打印带编号的列表，每行显示编号、上游 name、仓库内路径、描述的第一行，以及状态。状态有四种：已安装的标 `installed as <安装名>`；上游 name 不符合命名规范的标 `invalid name`；命中保留名的标 `reserved`；和清单里的 skill 或已有目录同名的标 `name taken`。
3. 输入要安装的编号，用逗号分隔，也可以写 `3-6` 这样的范围。默认一项都不选，直接回车就取消。选中已安装的条目不会重复安装。
4. 一次选了多个新 skill 时，提示输入统一前缀，回车表示不加。命令行已经带了 `--prefix` 时跳过这一步。加上前缀后，重新判断每一项是否重名、是否命中保留名。
5. 选中的条目里仍有冲突的，逐个提示输入别名，输入后重新检查，仍冲突就再问；回车则跳过这一项，其余照装。本次选中的几项之间互相重名也算。
6. 汇总将要安装的 skill 及其安装名，确认后开始安装。

仓库里只有一个 skill 时，跳过第 3、4 步，直接进入第 5 步；需要前缀时用 `--as` 或 `--prefix` 指定。

add 用哪个版本，取决于这个仓库里有没有 skill 正在使用：

- **没有**（第一次装这个仓库，或者它的 skill 都已删除）：取默认分支的最新提交，装完把它记为仓库版本；
- **有**：沿用清单记录的版本，不 fetch，免得同一仓库里已经装好的 skill 被顺带升级。开头会提示当前版本；想装上游新加的 skill，先运行 `skillctl update <owner/repo>`。

非交互方式的 add 也遵循同样的规则；遇到冲突时跳过冲突的那个并报告，其余照装，退出码为 1。

标准输入不是终端时（例如由 Agent 或脚本调用），只打印列表，然后以退出码 2 结束，不安装任何 skill，这种情况要用 `--skill` 指定。`--link` 也只能在非交互方式下使用。

## 同步逻辑

### 合并规则

两份清单的 skill 条目按 skill 标识、仓库版本按仓库名，分别逐条合并：

- 只有一边有的条目，直接保留；
- 两边都有的，取 `updated_at` 较晚的那整条记录；
- 时间完全相同时，保留本机的。

结果先写入临时文件，再用重命名的方式覆盖 `skills.json`。这样两台 Mac 在同步之前各自做的增删、改名都不会丢失；如果对同一个 skill 做了相反的操作，以时间较晚的为准。

skill 条目和仓库版本分开记录时间，是为了让改名和升级互不覆盖：一台给某个 skill 改名、另一台升级了它所在的仓库，合并后两项改动都保留。同一个仓库副本只能停在一个提交上，所以版本按仓库记录，不按 skill 记录。

合并只在两个地方发生：sync 拉取工作 clone 时，以及 merge 导入另一台的文件时。

### 拉取工作 clone

`skillctl sync` 的第一步是拉取工作 clone：

1. 如果工作 clone 里留有上次中断的临时文件 `.git/skillctl-pending.json`，先把它按合并规则并入 `skills.json`，再删除这个临时文件。
2. 在工作 clone 里执行 `git fetch`。网络不通时跳过拉取并提示，继续使用本地清单。
3. 远端没有新提交时，这一步到此结束。
4. 远端有新提交时，读取本地的 `skills.json`（可能带着未提交的修改）和远端最新提交里的 `skills.json`，按合并规则算出结果，先写入 `.git/skillctl-pending.json`。`.git` 里的文件不会出现在 `git status` 里，也不会被提交。
5. 撤销 `skills.json` 未提交的修改，然后执行 `git merge --ff-only`。
6. 用临时文件覆盖 `skills.json`，临时文件随之消失。
7. 如果无法快进，例如工作 clone 里有本地提交，或者其他文件的修改挡住了快进，就保持仓库不动，照样用临时文件覆盖 `skills.json`，并报告原因。

第 5 步和第 6 步之间如果出错，临时文件还留在 `.git` 里，下次 sync 的第 1 步会把它合并回来，本地的修改不会丢失。

快进之后，`git diff skills.json` 里剩下的，就是本机改了、但远端还没有的条目。在副机上，这就是还没传回主力机的改动。主力机 merge 并推送之后，副机再运行一次 sync，这个 diff 就会变成空的，说明改动已经送达。工具本身也随工作 clone 一起更新，但更新后的代码从下一次运行才生效。

### 导入另一台的清单

`skillctl merge <文件>` 的执行步骤：

1. 先完整执行一次 sync。
2. 校验传入的文件，顶层必须同时有 `version` 和 `skills` 字段。
3. 按合并规则算出结果，列出新增、删除、改名的条目和变化的仓库版本，等你确认。回答 `y` 之外的内容都会取消，清单和本机安装不变；标准输入不是终端时只列出、不合并，要加 `--yes` 才执行。
4. 确认后写入清单，对有变化的条目执行下一节的安装与卸载规则。

传入的文件不会被移动或删除。在主力机上执行完之后，由你提交并推送清单。

### 安装与卸载

合并完成后，`skillctl sync` 先检查清单内部有没有冲突：如果两个 `present` 条目的安装名相同（两台各自用同一个名字装了不同来源的 skill 时会出现），`updated_at` 较早的那条照常处理，较晚的那条跳过并报告，由你用 `add --as` 改名解决。安装名不符合命名规范的条目也跳过并报告，不会被拼进安装路径。

接下来把每个有 `present` 条目的仓库副本切到清单记录的提交：副本不存在就浅 clone，缺的副本并发 clone；本地缺这个提交就只拉它一个；副本里已跟踪的文件有改动时不切换，报告后跳过这个仓库的条目；清单没有记录版本的，补记副本当前的提交。

然后逐条处理 `present` 条目。下文用 T 表示 `~/.agents/skills/<安装名>`，用 L 表示 `~/.claude/skills/<安装名>`。

| T 的现状 | skillctl 的动作 |
|---|---|
| 不存在 | 先做和 add 相同的名字检查：命名规范、保留名，以及 `~/.agents/skills`、`~/.claude/skills`、`~/.codex/skills` 里的同名目录（本条目自己装的 T 和指向 T 的 L 不算）。任何一项不过，T 和 L 都不装，报告名字冲突，免得几个工具里同名却是不同的 skill。当前项目的 skill 目录只在 add 时检查，sync 不看，结果不取决于在哪个目录运行。检查通过后，从副本复制该路径（排除 `.git`、`.DS_Store` 和 `node_modules`），把 SKILL.md 第一段 frontmatter 里的 `name:` 改成安装名，然后写入标记文件 |
| 标记属于本条目，内容与标记里的哈希一致，提交号也与仓库版本一致 | 不做任何改动 |
| 标记属于本条目，内容与哈希一致，但提交号不同 | 重新复制。另一台 update 之后本机 sync，走的就是这一条 |
| 标记属于本条目，但内容与哈希不一致 | 不覆盖，报告 `modified locally` |
| 没有标记，或者标记属于其他条目 | 不覆盖，报告名字冲突 |

- **链接安装的条目**：T 应该是指向仓库副本根目录的软链接。不存在就创建（名字检查不过时同样两处都不装），指向别处就报告冲突。
- **L 的处理**：不存在就创建指向 T 的软链接；已经是指向 T 的软链接就不动；其他情况一律报告冲突，不覆盖。
- **已经装上的条目不再做名字检查**：先到先得，之后才出现的同名目录由 check 报告。
- **改名后留下的旧目录**：标记属于某个条目，但目录名已经不是该条目当前的安装名。内容没改过就删除这个旧目录，以及指向它的 L；改过就保留并报告。
- **`removed` 条目**：T 带有本条目的标记且内容没改过，就删除 T 和指向 T 的 L；内容改过就保留并报告。链接安装的条目只删除软链接，不动仓库副本。
- **清单里完全找不到对应条目的托管 skill**（例如清单文件丢了）：只报告，不删除。删除操作只能由 `removed` 记录触发。
- **未托管的 skill**：没有标记文件、也不是指向仓库副本的软链接，skillctl 不读写、不删除，也不写进清单。清单里的 skill 和它同名时，那一条不安装并报告名字冲突，由你改名解决。sync 和 list 结束时列出全部未托管的 skill，能从 `.openskills.json` 查到来源的附带纳入管理的 add 命令。

标记文件 `.skillctl.json` 记录三项内容：skill 标识、安装时的提交号，以及安装完成后目录内容的哈希。哈希用 SHA-256 计算：先按相对路径排序，再依次计入每个文件的路径和内容，计算时排除标记文件本身，以及 `.git`、`.DS_Store`、`node_modules`。新增、删除文件都会改变哈希。

一个仓库的最后一个 skill 被删除后，它的仓库版本记录保留，仓库副本也留在本机，但 sync、update、check 都不再处理这个仓库。以后再 add 它的 skill 时，按新仓库对待，取默认分支的最新提交。副本可以手动删除，需要时会重新 clone。

### 更新

`skillctl update [<owner/repo>]` 的执行步骤：

1. 对涉及的每个仓库副本并发执行 `git fetch --depth 1`。远端默认分支的最新提交等于仓库版本的，直接跳过。
2. 对该仓库下每个 `present` 条目，用 `git diff` 比较当前提交和远端最新提交在该路径下有没有变化，列出有变化的 skill 以及改动了哪些文件。
3. 如果远端最新提交里，该路径下的 SKILL.md 已经不存在（上游删掉了这个 skill，或者挪了位置），就保留已安装的版本并报告，由你决定是 remove 还是重新 add。
4. 把仓库副本切到远端最新提交，写入清单作为新的仓库版本，再对有变化的 skill 走一遍上面的安装规则。本地手改过的 skill 不会被覆盖。在主力机上提交推送后，副机 sync 时装同一版本。
5. 上游改了 `name:` 时，安装名不跟着变：安装时仍写回清单里的安装名。

agent_skills 自己（工作 clone 的 origin 对应的仓库）例外：在用的 skill 目录在两个提交之间都没有变化时，保持原来的仓库版本，不切换副本，也不改清单。它同时放着清单，每次提交清单都会产生新提交，按提交号判断会让"update、提交清单、又有新提交"无限循环。在用整个仓库（路径为 `.`）时仍按提交号判断。

### 检查

`skillctl check` 既不修改清单，也不修改已安装的 skill，只报告以下问题：

- 工作 clone 落后于远端，或者有本地提交；
- `skills.json` 有未提交的修改。在主力机上，说明还没提交推送；在副机上，说明还有改动没传回主力机；
- 清单与本机的安装状态不一致，也就是需要运行 sync 的项，包括仓库没有记录版本、仓库副本或已装 skill 不在记录的版本；
- 清单里的安装名不符合命名规范；
- 名字冲突。扫描范围是 `~/.agents/skills`、`~/.claude/skills`、`~/.codex/skills`、Codex 自带 skill 所在的 `~/.codex/skills/.system`，以及当前目录下的 `.agents/skills` 和 `.claude/skills`，不归 skillctl 管的目录也包括在内。判断方法是按名字分组：同一组里的目录，解析软链接后是同一个目录，或者内容哈希完全相同，就不算冲突。所以全局 L 与 T 这一对，以及项目里两个 skill 目录中内容相同的那一对，都不会被误报；
- 被本地手改过的托管 skill；
- 失效的软链接；
- 目录名与 `name:` 不一致的 skill；
- 上游默认分支的最新提交不等于仓库版本的仓库。agent_skills 自己例外：用工作 clone 比较仓库版本和远端最新提交，在用的 skill 目录有变化才报告，只改了清单或 README 不算。

只要发现任意一项，退出码就是 1。

各仓库的上游查询并发进行，最多 16 个同时查，每个最多等 30 秒。update 拉取上游、新电脑第一次 sync 时 clone 仓库副本，也按同样的方式并发。网络卡住时尽快失败：SSH 连接和保活各等 15 秒；HTTPS 传输连续 30 秒低于 1KB/s 就放弃。clone 和拉取不设总时长上限，慢但一直在传的大仓库照样能完成。

## 命名与冲突规则

- **安装名必须符合 Agent Skills 规范**：1 到 64 个字符，只能包含小写字母、数字和连字符，不能以连字符开头或结尾，不能有连续的连字符。冒号和斜杠都不允许。
- **默认安装名**：不带 `--as` 时，安装名取上游 SKILL.md 里的 `name:`。上游的 name 不符合规范时拒绝安装，要求你用 `--as` 指定。
- **默认保留原名，按需加前缀**：不给所有 skill 统一加作者前缀。只有重名、命中保留名，或者是一整套含很多泛名的套件（例如 gstack、mattpocock）时，才加前缀。前缀优先用项目名或仓库名，例如 `gstack-`，不用作者账号名。
- **先到先得**：已经装上的 skill，名字不会因为后来者而改变。新装的 skill 如果和清单里的 skill 同名，或者和 `~/.agents/skills`、`~/.claude/skills`、`~/.codex/skills` 里的已有目录同名，就拒绝安装；add 还会检查当前项目的 `.agents/skills` 和 `.claude/skills`。未托管的目录也算，所以副机上自己维护的 skill 同样会拦下新装的同名 skill，并提示用 `--as <项目或仓库简称>-<原名>` 起别名，或者用 `--prefix` 加前缀。
- **add 和 sync 用同一套检查**：命名规范、保留名和三个全局目录的检查由同一个函数完成，add 选名时在此之外再检查清单、本次选中的其他项和当前项目目录。这样 add 拦得住的，sync 在另一台新装时也拦得住。
- **`--prefix` 的规则**：
  - 安装名等于前缀加上游 `name:`；前缀末尾没有连字符时自动补上；
  - 上游 name 已经以这个前缀开头的，不重复加，例如 `baoyu-cover-image` 配 `--prefix baoyu-`，安装名仍是 `baoyu-cover-image`；
  - 只作用于这次新装的 skill，已经装好的 skill 不会因此改名，改名仍用 `--as`；
  - 不能和 `--as` 同时使用；
  - 加完前缀的安装名同样要符合规范，并通过重名和保留名检查；
  - 清单里只记录最终的安装名，不记录前缀。
- **不改写正文里的引用**：skill 正文里对其他 skill 的引用，工具不做改写。例如 `writing-plans` 里写的 `superpowers:executing-plans`，它指向的 skill 本来就没有安装，改写解决不了问题。

### 保留名

命中保留名时拒绝安装，要求用 `--as` 或 `--prefix` 换一个名字。保留名由四部分组成：

| 类别 | 名字 | 维护方式 |
|---|---|---|
| `third_party/` 里已经出现过的泛名（12 个） | `review`、`qa`、`ship`、`spec`、`learn`、`health`（gstack）；`tdd`、`research`、`triage`、`teach`、`code-review`（mattpocock-skills）；`retro`（两者都有） | 写在 `skillctl.py` 里 |
| Claude Code 自带的 skill 名和别名（17 个，不含上一行已有的 `review`、`code-review`） | `batch`、`claude-api`、`dataviz`、`debug`、`design`、`design-sync`、`doctor`、`fewer-permission-prompts`、`loop`、`run`、`run-skill-generator`、`simplify`、`update-config`、`verify`、`workflow-authoring`，别名 `checkup`、`proactive` | 写在 `skillctl.py` 里，Claude Code 新增自带 skill 时手动补充 |
| 容易被第三方 skill 用到的 Claude Code 内置命令（3 个） | `init`、`schedule`、`security-review` | 写在 `skillctl.py` 里 |
| Codex 自带的 skill | 例如 `imagegen`、`openai-docs`、`plugin-creator`、`review-agent`、`skill-creator`、`skill-installer` | 每次运行时从 `~/.codex/skills/.system/` 读取，Codex 升级后自动跟上 |

Claude Code 的名单取自官方命令文档里标为 Skill 的条目。文档写明：个人 skill 和自带 skill 同名时，会替换掉自带的那个。skill 和内置命令同名时哪个生效，文档没有写，但无论哪个生效，都有一方用不了。

## 两台 Mac 的日常流程

| 场景 | 你要做的 | 另一台什么时候生效 |
|---|---|---|
| 在主力机上 add 或 remove | 提交并推送工作 clone 里的 `skills.json` | 副机下一次运行任意 skillctl 命令时 |
| 在副机上 add 或 remove | 不提交。把副机工作 clone 里的 `skills.json` 拷到主力机任意位置，在主力机上运行 `skillctl merge <文件>`，然后提交并推送 | 主力机运行 merge 时；之后副机再 sync，`git diff skills.json` 变成空的 |
| 在主力机上 update | 提交并推送工作 clone 里的 `skills.json` | 副机下一次运行任意 skillctl 命令时，切到同一版本 |
| 在副机上 update | 和副机上的 add、remove 一样，把清单拷到主力机 merge | 主力机运行 merge 时 |
| 在主力机上修改自建 skill 并推送到 GitHub | 主力机运行 `skillctl update Viva5649/agent_skills`，再提交推送 `skills.json` | 副机下一次运行任意 skillctl 命令时 |
| 新电脑 | 按 README「在新电脑上安装」操作 | 第一次 sync 时装齐 |

## 已知限制

- **同步都要手动触发。** skillctl 不接入任何定时任务。主力机的改动要你提交推送，副机运行 skillctl 时才会拿到；副机的改动要你把清单拷到主力机并 merge。以后需要自动同步的话，主力机可以在定时维护里加一步 `skillctl sync`，副机可以加一个 launchd 定时任务。
- **副机的工作 clone 会带着未提交的修改。** 副机上不要在这个 clone 里提交，更新仓库用 `skillctl sync`。直接 `git pull` 也不会丢数据：远端也改了 `skills.json` 时，git 会拒绝执行，提示本地有修改。
- **工具更新晚一次生效。** sync 先拉取工作 clone 再安装，但这一次运行的仍是拉取前的代码。skillctl 本身有行为修复时，副机要先单独 `git pull --ff-only`，再运行 sync。
- **git 历史里只有主力机的提交。** 副机的改动要等主力机 merge 并推送之后，才会出现在 git 历史里。
- **自建 skill 要走两步才生效。** 先把 skill 推送到 GitHub，再在主力机上 update 并推送清单，副机 sync 后才装上新版本。
- **副机本机已有同名 skill 时会一直报冲突。** 例如在副机上开发、再拷进 agent_skills 的 skill，进了清单之后，副机 sync 会对这些条目报名字冲突，两处都不装，退出码为 1。副机自己那份不受影响。
- **链接安装的 gstack 没有标记文件。** 它的安装目录直接指向仓库副本，仓库副本里已跟踪的文件有改动时，sync 和 update 都不切换版本，只报告；要升级得先还原这些改动。它安装时自己生成、被 git 忽略的文件不受影响。
- **正文里 skill 之间的引用不改写。**
- **相反操作以较晚的为准。** 同一个 skill 在同步之前被两台做了相反的操作时，以时间较晚的那次为准。两台的时钟都由系统自动校准，误差可以忽略。
- **上游挪目录要重新 add。** 上游挪动了 skill 目录时，update 会报告 SKILL.md 已不存在，需要 remove 后按新路径重新 add。
- **Codex 是否递归扫描尚未确认。** Codex 文档没有明确说明是否递归扫描子目录，gstack 链接安装之后，Codex 会不会把 gstack 仓库里的其他 skill 也带出来，需要在 Codex 的 skill 列表里确认。
