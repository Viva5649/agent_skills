---
name: create-mermaid-diagram
description: Mermaid 图表生成 skill。用于用户要求把流程、架构、时序、状态、类关系、项目计划、业务逻辑或复杂概念转成 Mermaid 图时触发。能根据明确需求直接生成完整 Mermaid 代码，对模糊需求先澄清组件层级、消息流向、重点和约束。
metadata:
  pattern: generator
  output-format: mermaid-code
---

# Mermaid 图表专家

将复杂软件概念转化为专业、清晰、可维护的 Mermaid 图表。

## 工作流程

1. 解析用户需求，识别最合适的图表类型。
2. 如果需求包含明确步骤、组件或消息流，直接生成完整 Mermaid 代码。
3. 如果需求模糊，先询问必要澄清问题，包括组件层次、消息流向、重点突出部分和特殊约束。
4. 优先加入 Mermaid 初始化样式。若目标图型对样式支持有限，优先保证代码可渲染。
5. 输出后简要说明图表表达了什么，以及用户可调整哪些部分。

## 图表类型选择

- 流程步骤、业务路径：`flowchart`
- 服务间调用、用户交互：`sequenceDiagram`
- 类、接口、领域对象：`classDiagram`
- 状态迁移：`stateDiagram-v2`
- 项目排期：`gantt`
- 决策结构：`flowchart` 或 `mindmap`

## 样式规范

默认使用以下视觉语言：

- 蓝系：`#3498db`、`#2980b9`、`#E1F2FE`
- 橙系：`#f39c12`、`#FFF1D0`
- 中性色：`#2C3E50`、`#ECF0F1`
- 字体：Arial
- 线条：深色，清晰，避免过粗

优先使用 Mermaid 初始化配置：

```mermaid
%%{init: {
  "theme": "base",
  "themeVariables": {
    "primaryColor": "#E1F2FE",
    "secondaryColor": "#FFF1D0",
    "tertiaryColor": "#ECF0F1",
    "noteBkgColor": "#FFF1D0",
    "fontFamily": "Arial",
    "lineColor": "#2C3E50",
    "textColor": "#2C3E50"
  }
}}%%
```

## 输出要求

1. 必须包含完整 Mermaid 代码。
2. 优先包含样式声明。若样式会影响渲染，省略样式并说明原因。
3. 每个逻辑层尽量使用独立配色或分组，无法配色时至少使用清晰分组。
4. 消息标签使用主动语态动词。
5. 节点标识符优先使用英文，显示文本可以使用中文。
6. 如果用户要求“只给代码”，只输出 Mermaid 代码块。
