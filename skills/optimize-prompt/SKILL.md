---
name: optimize-prompt
description: 提示词优化 skill。用于用户想优化、改写、诊断、创建或系统化提示词时触发。适合“帮我优化这个 prompt”“把这个需求写成提示词”“选一个提示词框架”等场景。会基于 57 个提示词框架选择合适结构，必要时先澄清目标、受众、上下文、格式和约束。
metadata:
  pattern: tool-wrapper
  references: references/Frameworks_Summary.md
---

# 提示词优化

把模糊需求、原始 prompt 或任务描述转化为清晰、稳定、可复用的高质量提示词。

## 工作流程

### 步骤 1：分析用户输入

判断用户输入属于哪一种：

- 原始 prompt，需要优化。
- 任务描述，需要转成 prompt。
- 模糊想法，需要先澄清。
- 已有提示词框架，需要诊断和增强。

### 步骤 2：匹配场景并选择框架

读取 `references/Frameworks_Summary.md`，根据应用场景、复杂度和领域选择最合适的框架。

复杂度参考：

| 复杂度 | 推荐框架 |
| --- | --- |
| 简单，3 要素以内 | APE、ERA、TAG、RTF、BAB、PEE、ELI5 |
| 中等，4 到 5 要素 | RACE、CIDI、SPEAR、SPAR、FOCUS、SMART、GOPA、ORID、CARE、ROSES、PAUSE、TRACE、GRADE、TRACI、RODES |
| 复杂，6 要素以上 | RACEF、CRISPE、SCAMPER、Six Thinking Hats、ROSES、PROMPT、RISEN、RASCEF、Atomic Prompting |

领域参考：

| 领域 | 推荐框架 |
| --- | --- |
| 营销内容 | BAB、SPEAR、Challenge-Solution-Benefit、BLOG、PROMPT、RHODES |
| 决策分析 | RICE、Pros and Cons、Six Thinking Hats、Tree of Thought、PAUSE、What If |
| 教育培训 | Bloom's Taxonomy、ELI5、Socratic Method、PEE、Hamburger Model |
| 产品开发 | SCAMPER、HMW、CIDI、RELIC、3Cs Model |
| AI 对话或助手 | COAST、ROSES、TRACE、RACE、RASCEF |
| 写作创作 | BLOG、4S Method、Hamburger Model、Few-shot、RHODES、Chain of Destiny |
| 图像生成 | Atomic Prompting |
| 快速简单任务 | Zero-shot、ERA、TAG、APE、RTF |
| 复杂推理 | Chain of Thought、Tree of Thought |

### 步骤 3：加载框架详情

确定框架后，读取 `references/frameworks/` 中对应文件。

文件命名模式：`XX_FrameworkName_Framework.md`。

例：选择 RACEF 时读取 `references/frameworks/01_RACEF_Framework.md`。

### 步骤 4：澄清关键信息

在生成最终 prompt 前，检查以下信息是否足够：

1. 目标是否明确。
2. 输出面向谁。
3. 背景上下文是否充分。
4. 输出格式是否明确。
5. 约束条件是否完整。

如果缺失会显著影响质量，先问澄清问题。若用户希望快速给出版本，可以基于合理假设先产出，并标注假设。

### 步骤 5：生成优化后的 prompt

应用所选框架：

1. 按框架组件组织提示词。
2. 合并用户提供和澄清得到的信息。
3. 明确角色、任务、上下文、步骤、约束、输出格式和质量标准。
4. 根据需要加入示例。
5. 保持语言直接、可执行、无歧义。

### 步骤 6：呈现并迭代

输出包含：

```markdown
## 选择的框架
<框架名称，以及为什么适合>

## 优化后的提示词
<完整 prompt>

## 结构说明
- <框架元素 1 是如何应用的>
- <框架元素 2 是如何应用的>

## 可选变体
- <适合更短输出的变体>
- <适合更严格输出的变体>
```

如果用户要求修改，保留框架优势并快速迭代。

## 快速选择表

| 用户表达 | 优先框架 |
| --- | --- |
| 我需要一个简单 prompt | APE、ERA、TAG |
| 我要说服或销售 | BAB、SPEAR、Challenge-Solution-Benefit |
| 我要分析或决策 | RICE、Pros and Cons、Chain of Thought |
| 我要教学或解释 | ELI5、Bloom's Taxonomy、Socratic Method |
| 我要创意 | SCAMPER、HMW、SPARK、Imagine |
| 我要结构化写作 | BLOG、4S Method、Hamburger Model |
| 我要逐步推理 | Chain of Thought、Tree of Thought |
| 我要生成图片 | Atomic Prompting |
| 我要详细计划 | RISEN、RASCEF、CRISPE |

## 质量标准

- 优化后的 prompt 要能直接复制使用。
- 不只润色措辞，要改善结构、约束和可执行性。
- 解释为什么选择该框架，帮助用户下次复用。
- 不确定时先澄清，用户赶时间时先给可用版本。
