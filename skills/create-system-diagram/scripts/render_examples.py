#!/usr/bin/env python3
"""Generate three editable layout examples using the package's HTML palette."""
import argparse
from html import escape
import math
from pathlib import Path
import re


PACKAGE = Path(__file__).resolve().parents[1]


def port(box, side):
    x, y, w, h = box
    return {"top": (x + w / 2, y), "bottom": (x + w / 2, y + h),
            "left": (x, y + h / 2), "right": (x + w, y + h / 2)}[side]


def label_anchor(points, lines=1, side="right"):
    """A candidate on the longest segment; the rendered label still needs review."""
    a, b = max(zip(points, points[1:]), key=lambda pair: math.dist(*pair))
    x, y = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    if a[1] == b[1]:
        return x, y - 14 - (lines - 1) * 20, "middle"
    return x + (16 if side == "right" else -16), y - (lines - 1) * 10, "start" if side == "right" else "end"


def text(x, y, value, cls="note", attrs=""):
    return f'<text class="{cls}" x="{x:g}" y="{y:g}" {attrs}>{escape(value)}</text>'


def card(node):
    name, box, role, title, body = node
    x, y, w, h = box
    return (f'<g id="{name}" class="role-{role}"><rect class="card" x="{x}" y="{y}" width="{w}" height="{h}"/>'
            + text(x + 18, y + 31, title, "node-title")
            + "".join(text(x + 18, y + 56 + i * 20, line) for i, line in enumerate(body)) + '</g>')


def frame(box, title, role="neutral"):
    x, y, w, h = box
    return (f'<g class="role-{role}"><rect class="frame" x="{x}" y="{y}" width="{w}" height="{h}"/>'
            + text(x + 20, y + 28, title, "frame-title") + '</g>')


def edge(name, start, end, kind="flow", label=(), via=(), label_side="right"):
    route = [start, *via, end]
    if any(a == b or (a[0] != b[0] and a[1] != b[1]) for a, b in zip(route, route[1:])):
        raise ValueError(f"{name}: 连线须为非零正交线段")
    path = "M" + " L".join(f"{x:g},{y:g}" for x, y in route)
    result = f'<path id="{name}" class="edge k-{kind}" d="{path}" marker-end="url(#sample-arrow-{kind})"/>'
    if label:
        x, y, anchor = label_anchor(route, len(label), label_side)
        for i, line in enumerate(label):
            cls = f"edge-label k-{kind}" + (" edge-operation" if len(label) > 1 and i == 0 else "")
            result += text(x, y + i * 20, line, cls, f'data-edge-label="{name}" text-anchor="{anchor}"')
    return result


def legend(y, kinds):
    return "".join(edge(f"legend-{kind}", (40, y + i * 28), (92, y + i * 28), kind)
                   + text(108, y + i * 28 + 4, label, f"edge-label k-{kind}", 'data-legend="true"')
                   for i, (kind, label) in enumerate(kinds))


def layered():
    nodes, backgrounds, links = [], [], []
    rows = [
        ("business", "公开能力", [("query", "查询入口", ["接收查询请求"]), ("submit", "任务入口", ["接收提交请求"])]),
        ("orchestration", "编排与协调", [("query-runtime", "查询编排", ["组织查询步骤"]), ("task-runtime", "任务编排", ["组织任务步骤"])]),
        ("infrastructure", "公共基础设施", [("config", "通用配置", ["提供查询参数"]), ("storage", "结果存储", ["保存任务结果"])])]
    for row, (role, title, items) in enumerate(rows):
        y = 50 + row * 230
        backgrounds.append(frame((40, y, 1320, 140), title, role))
        for col, (name, title, body) in enumerate(items):
            nodes.append((name, (60 + col * 660, y + 50, 620, 70), role, title, body))
    boxes = {n[0]: n[1] for n in nodes}
    for name, src, dst, kind, label in [
        ("query-call", "query", "query-runtime", "flow", ("R1 · 提交查询", "调用查询编排接口")),
        ("task-call", "submit", "task-runtime", "flow", ("R2 · 提交任务", "调用任务编排接口")),
        ("read-config", "query-runtime", "config", "plain", ("读取通用配置",)),
        ("write-result", "task-runtime", "storage", "plain", ("写入任务结果",))]:
        links.append(edge(name, port(boxes[src], "bottom"), port(boxes[dst], "top"), kind, label))
    return ("连续分层（通用示例）", 790, backgrounds, nodes, links,
            legend(710, [("flow", "能力调用"), ("plain", "组件依赖")]),
            "R1、R2 是关系索引，不表示执行顺序。配置与存储只接收图中明确画出的依赖；不同列不暗示共享实例。")


def parallel():
    nodes, backgrounds, links = [], [], []
    rows = [("分析工作流", [("source", "business", "输入材料", ["提供待分析内容"]),
                         ("analysis", "orchestration", "分析编排", ["组织分析与归纳"]),
                         ("draft", "infrastructure", "分析产物", ["保存分析结果"])]),
            ("核查工作流", [("candidate", "business", "候选材料", ["提供待核查内容"]),
                         ("review", "governance", "独立核查", ["检查事实与约束"]),
                         ("report", "infrastructure", "核查产物", ["保存核查结论"])])]
    for row, (title, items) in enumerate(rows):
        y = 50 + row * 250
        backgrounds.append(frame((40, y, 1320, 190), title + "（示例）"))
        lane = []
        for col, (name, role, title, body) in enumerate(items):
            node = (name, (70 + col * 470, y + 60, 320, 100), role, title, body)
            nodes.append(node)
            lane.append(node)
        for i, (src, dst) in enumerate(zip(lane, lane[1:])):
            links.append(edge(f"workflow-{row}-{i}", port(src[1], "right"), port(dst[1], "left"),
                              label=("传入材料" if i == 0 else "交付结果",)))
    return ("并列工作流（通用示例）", 610, backgrounds, nodes, links,
            legend(550, [("flow", "工作流内的交接")]),
            "两条工作流分别展示参与者与产物归属；上下排列不表示先后执行。灰色外框表达工作流分组，组件颜色仍按职责选择。")


def loop():
    nodes = [(name, (60 + i * 340, 130, 260, 108), role, title, body)
             for i, (name, role, title, body) in enumerate([
                 ("request", "business", "任务入口", ["接收任务与约束"]),
                 ("execute", "orchestration", "任务执行", ["生成或修正同一份产物"]),
                 ("gate", "governance", "结果检查", ["检查通过才允许交付"]),
                 ("deliver", "infrastructure", "交付产物", ["保存通过检查的结果"])])]
    links = [edge(f"forward-{i}", port(src[1], "right"), port(dst[1], "left"), label=(label,))
             for i, (src, dst, label) in enumerate(zip(nodes, nodes[1:], ["提交", "检查", "通过"]))]
    start, end = port(nodes[2][1], "bottom"), port(nodes[1][1], "bottom")
    links.append(edge("retry", start, end, "alt", ("检查未通过 · 返回修正", "在同一任务内继续处理"),
                      via=((start[0], 350), (end[0], 350))))
    return ("带回路的局部流程（通用示例）", 520,
            [frame((40, 60, 1320, 320), "任务处理与质量检查")], nodes, links,
            legend(430, [("flow", "正常处理与通过分支"), ("alt", "检查未通过时返回修正")]),
            "回路在所属分组内预留独立通道，末端竖直接入执行组件。示例明确允许返回修正，不能据此推断真实项目也会自动重试。")


LAYOUTS = {"layered": layered, "parallel": parallel, "loop": loop}


def render(layout):
    template = (PACKAGE / "assets/architecture-template.html").read_text(encoding="utf-8")
    title, height, backgrounds, nodes, links, key, caption = LAYOUTS[layout]()
    defs = re.search(r"<defs>.*?</defs>", template, re.S).group()
    content = "\n".join([*backgrounds, *links, *(card(n) for n in nodes), key])
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" class="architecture" viewBox="0 0 1400 {height}" role="img" aria-labelledby="sample-title" aria-describedby="sample-description">'
           f'<title id="sample-title">{escape(title)}</title><desc id="sample-description">{escape(caption)}</desc>\n{defs}\n{content}\n</svg>')
    output = re.sub(r"<svg\b.*?</svg>", lambda _: svg, template, count=1, flags=re.S)
    output = re.sub(r"<title>.*?</title>", lambda _: f"<title>{escape(title)}</title>", output, count=1)
    output = re.sub(r"<h1>.*?</h1>", lambda _: f"<h1>{escape(title)}</h1>", output, count=1)
    return re.sub(r"<figcaption>.*?</figcaption>", lambda _: f"<figcaption>来源：内置通用示例，不描述真实项目。{escape(caption)}</figcaption>", output, count=1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--layout", choices=[*LAYOUTS, "all"], default="all")
    args = parser.parse_args()
    names = list(LAYOUTS) if args.layout == "all" else [args.layout]
    outputs = [(args.outdir / f"{name}.html", render(name)) for name in names]
    if any(path.exists() for path, _ in outputs):
        parser.error("目标示例已存在；请使用空目录，避免覆盖用户修改")
    args.outdir.mkdir(parents=True, exist_ok=True)
    for path, content in outputs:
        path.write_text(content, encoding="utf-8")
        print(path)


if __name__ == "__main__":
    main()
