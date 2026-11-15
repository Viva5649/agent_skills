#!/usr/bin/env python3
"""Generate editable layout examples using the package's HTML palette."""
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


def card(node, tinted=False, module_title=False):
    name, box, module, title, body = node
    x, y, w, h = box
    cls = "card card-tinted" if tinted else "card"
    return (f'<g id="{name}" class="{module}"><rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}"/>'
            + text(x + 18 if body else x + w / 2, y + 31 if body else y + h / 2 + 5,
                   title, "node-title module-name" if module_title else "node-title",
                   '' if body else 'text-anchor="middle"')
            + "".join(text(x + 18, y + 56 + i * 20, line, "body-text") for i, line in enumerate(body)) + '</g>')


def frame(box, title, module="group-neutral", style="frame"):
    x, y, w, h = box
    if module == "group-neutral":
        style = "annotation"
    return (f'<g class="{module}"><rect class="{style}" x="{x}" y="{y}" width="{w}" height="{h}"/>'
            + text(x + 20, y + 28, title, "section-title" if module == "group-neutral" else "frame-title") + '</g>')


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


def legend(kinds, modules=()):
    rows = [f'<div class="legend-row {module}"><span class="legend-symbol"><span class="legend-swatch"></span></span>'
            f'<span>{escape(label)}</span></div>' for module, label in modules]
    for kind, label in kinds:
        line = 'M0,9 H52' if kind == "association" else 'M0,9 H44'
        arrow = '' if kind == "association" else '<path class="legend-arrow" d="M44,5 L52,9 L44,13 Z"/>'
        rows.append(f'<div class="legend-row k-{kind}"><svg class="legend-symbol" width="52" height="18" viewBox="0 0 52 18" aria-hidden="true">'
                    f'<path class="legend-line" d="{line}"/>{arrow}</svg><span>{escape(label)}</span></div>')
    return '<div class="legend" role="group" aria-label="图例">\n' + '\n'.join(rows) + '\n</div>'


def layered():
    nodes, backgrounds, links = [], [], []
    rows = [
        ("module-entry", "公开能力", [("query", "查询入口", []), ("submit", "任务入口", [])]),
        ("module-orchestration", "编排与协调", [("query-runtime", "查询编排", ["组织查询步骤"]), ("task-runtime", "任务编排", ["组织任务步骤"])]),
        ("module-services", "公共基础设施", [("config", "通用配置", ["提供查询参数"]), ("storage", "结果存储", ["保存任务结果"])])]
    for row, (module, title, items) in enumerate(rows):
        y = 50 + row * 230
        backgrounds.append(frame((40, y, 1320, 140), title, module))
        for col, (name, title, body) in enumerate(items):
            nodes.append((name, (60 + col * 660, y + 50, 620, 70), module, title, body))
    boxes = {n[0]: n[1] for n in nodes}
    for name, src, dst, kind, label in [
        ("query-call", "query", "query-runtime", "flow", ("R1 · 提交查询", "调用查询编排接口")),
        ("task-call", "submit", "task-runtime", "flow", ("R2 · 提交任务", "调用任务编排接口")),
        ("read-config", "query-runtime", "config", "plain", ("读取通用配置",)),
        ("write-result", "task-runtime", "storage", "plain", ("写入任务结果",))]:
        links.append(edge(name, port(boxes[src], "bottom"), port(boxes[dst], "top"), kind, label))
    return ("连续分层（通用示例）", 680, backgrounds, nodes, links,
            legend([("flow", "能力调用"), ("plain", "组件依赖")],
                   [("module-entry", "公开能力"), ("module-orchestration", "编排与协调"), ("module-services", "公共基础设施")]),
            "R1、R2 是关系索引，不表示执行顺序。配置与存储只接收图中明确画出的依赖；不同列不暗示共享实例。本例追踪三个模块的协作，入口用红色、编排用紫色、公共设施用橙色，内部组件继承所属模块颜色。")


def parallel():
    nodes, backgrounds, links = [], [], []
    rows = [("分析工作流", [("source", "group-neutral", "输入材料", ["提供待分析内容"]),
                         ("analysis", "module-analysis", "分析编排", ["组织分析与归纳"]),
                         ("draft", "module-analysis", "分析产物", ["保存分析结果"])]),
            ("核查工作流", [("candidate", "group-neutral", "候选材料", ["提供待核查内容"]),
                         ("review", "module-review", "独立核查", ["检查事实与约束"]),
                         ("report", "module-review", "核查产物", ["保存核查结论"])])]
    for row, (title, items) in enumerate(rows):
        y = 50 + row * 250
        backgrounds.append(frame((40, y, 1320, 190), title + "（示例）"))
        lane = []
        for col, (name, module, title, body) in enumerate(items):
            node = (name, (70 + col * 470, y + 60, 320, 100), module, title, body)
            nodes.append(node)
            lane.append(node)
        for i, (src, dst) in enumerate(zip(lane, lane[1:])):
            links.append(edge(f"workflow-{row}-{i}", port(src[1], "right"), port(dst[1], "left"),
                              label=("传入材料" if i == 0 else "交付结果",)))
    return ("并列工作流（通用示例）", 520, backgrounds, nodes, links,
            legend([("flow", "工作流内的交接")],
                   [("module-analysis", "分析模块及产物"), ("module-review", "核查模块及产物")]),
            "两条工作流分别展示参与者与产物归属；上下排列不表示先后执行。中性外框表达工作流分组。分析模块用紫色，核查模块用绿色，产物沿用所属模块颜色；输入材料使用中性色。")


def loop():
    nodes = [(name, (60 + i * 340, 130, 260, 108), module, title, body)
             for i, (name, module, title, body) in enumerate([
                 ("request", "module-entry", "任务入口", ["接收任务与约束"]),
                 ("execute", "module-execution", "任务执行", ["生成或修正同一份产物"]),
                 ("gate", "module-review", "结果检查", ["检查通过才允许交付"]),
                 ("deliver", "module-execution", "交付产物", ["保存通过检查的结果"])])]
    links = [edge(f"forward-{i}", port(src[1], "right"), port(dst[1], "left"), label=(label,))
             for i, (src, dst, label) in enumerate(zip(nodes, nodes[1:], ["提交", "检查", "通过"]))]
    start, end = port(nodes[2][1], "bottom"), port(nodes[1][1], "bottom")
    links.append(edge("retry", start, end, "alt", ("检查未通过：返回修正", "在同一任务内继续处理"),
                      via=((start[0], 350), (end[0], 350))))
    return ("带回路的局部流程（通用示例）", 410,
            [frame((40, 60, 1320, 320), "任务处理与质量检查")], nodes, links,
            legend([("flow", "正常处理与通过分支"), ("alt", "检查未通过时返回修正")],
                   [("module-entry", "任务入口"), ("module-execution", "执行模块及产物"), ("module-review", "检查模块")]),
            "入口用红色、执行模块及产物用蓝色、检查模块用绿色。配色用于追踪本例协作对象；回路预留独立通道，末端竖直接入执行组件。示例明确允许返回修正，不能据此推断真实项目也会自动重试。")


def scenario():
    application_box, service_box = (40, 60, 440, 288), (920, 60, 440, 288)
    performance_box = (40, 410, 1320, 248)
    backgrounds = [text(40, 30, "资料应用通过同一索引服务查询与更新资料；以下指标均为模拟数据。", "body-text"),
                   frame(application_box, "资料应用", "module-application"),
                   frame(service_box, "索引服务", "module-index"),
                   frame(performance_box, "索引服务性能基线与目标", "module-index", "annotation"),
                   frame((40, 700, 640, 190), "索引服务本期工作", "module-index", "annotation"),
                   frame((720, 700, 640, 190), "索引服务质量验收", "module-index", "annotation")]
    for x, module, duties in [
        (60, "module-application", [("查询资料", "提交查询条件，展示匹配内容"), ("更新资料", "提交资料变更，记录更新结果")]),
        (940, "module-index", [("查询处理", "检索匹配条目，返回排序结果"), ("索引更新", "应用资料变更，返回更新状态")])]:
        for i, (title, body) in enumerate(duties):
            y = 110 + i * 116
            backgrounds.append(f'<g class="{module}"><rect class="duty" x="{x}" y="{y}" width="400" height="100"/>'
                               + text(x + 18, y + 31, title, "node-title")
                               + text(x + 18, y + 60, body, "body-text") + '</g>')
    links = []
    for key, y, request, result in [("query", 138, "查询：查询条件", "查询：匹配内容"),
                                     ("update", 254, "更新：资料变更", "更新：更新状态")]:
        links.extend([edge(f"{key}-request", (480, y), (920, y), "plain", (request,)),
                      edge(f"{key}-return", (920, y + 54), (480, y + 54), "plain", (result,))])
    x, y = port(service_box, "bottom")
    _, end_y = port(performance_box, "top")
    links.append(f'<path id="performance-owner" class="edge k-association" d="M{x:g},{y:g} V{end_y:g}"/>'
                 + text(x + 16, (y + end_y) / 2, "性能数据归属", "edge-label k-association", 'data-edge-label="performance-owner"'))
    backgrounds.extend([
        text(60, 464, "固定查询集，单请求；每档测量 5 次，取中位数"),
        '<g class="module-index"><rect class="card" x="60" y="484" width="600" height="130"/>'
        + text(78, 508, "不同资料规模的查询耗时", "node-title")
        + "".join(text(78, y, scale, "body-text") + text(642, y, value, "metric-value", 'text-anchor="end"')
                  for y, scale, value in [(537, "100 条资料", "18 ms"), (565, "500 条资料", "36 ms"), (593, "2000 条资料", "90 ms")]) + '</g>',
        '<g class="module-index"><rect class="card" x="680" y="484" width="300" height="130"/>'
        + text(698, 508, "已测内存范围", "node-title") + text(698, 546, "12 至 28 MiB", "metric-value")
        + text(698, 578, "空闲时：12 MiB", "body-text") + text(698, 598, "查询时：28 MiB", "body-text") + '</g>',
        '<g class="module-index"><rect class="card" x="1000" y="484" width="340" height="130"/>'
        + text(1018, 508, "查询耗时：模拟基线 → 目标", "node-title")
        + '<text class="metric-value" x="1018" y="546">36 → <tspan class="metric-target">≤ 30 ms</tspan></text>'
        + text(1018, 578, "500 条资料；测量口径同左") + '</g>',
        text(60, 638, "数据来源：通用示例中的模拟测量；实际使用时替换数值、来源与口径。"),
        text(60, 768, "现状：每次查询重新解析配置", "body-text"),
        text(60, 804, "本期：复用已解析的查询配置", "node-title"),
        text(60, 836, "预期结果：减少重复解析", "body-text"),
        text(740, 752, "测试人员使用同一资料集与查询集，覆盖三档规模。", "body-text"),
        text(740, 778, "在相同配置与统计口径下，记录优化前后的耗时与结果。", "body-text"),
        text(740, 808, "通过条件：", "node-title"),
        text(740, 834, "查询结果与基线一致，且", "body-text"),
        '<text class="body-text" x="740" y="862">500 条资料的查询耗时中位数达到目标 <tspan class="metric-target">≤ 30 ms</tspan></text>'])
    key = legend([("plain", "请求与结果交接"), ("association", "性能数据归属")],
                 [("module-application", "资料应用"), ("module-index", "索引服务及性能、工作和验收说明")])
    return ("场景能力与验收（通用示例）", 920, backgrounds, [], links, key,
            "资料应用用淡红色，索引服务用橙色。查询与更新的返回线均接回原调用方；块内说明各模块在两个场景中的作用。"
            "性能、工作和验收区沿用索引服务的归属配色，正文与当前值用正文色，目标数值及比较符号局部橙色加粗。"
            "组件、数值与验收条件均为虚构示例，使用时按实际任务替换。")


def nested():
    body = ['<g id="retrieval-system" class="module-retrieval">',
            '<rect class="frame" x="24" y="24" width="1352" height="562"/>',
            text(50, 67, "资料检索系统", "outer-title"),
            text(1350, 65, "外层模块", "module-type", 'text-anchor="end"'),
            text(50, 99, "组织资料查询、索引更新与结果交付", "duty-body")]
    modules = [("information-application", 50, 324, "资料应用", [
                   ("request-responsibility", 72, 270, 280, 110, "组织请求", ["提交查询或资料变更"]),
                   ("presentation-responsibility", 72, 402, 280, 126, "呈现结果", ["展示查询结果与更新状态"])]),
               ("index-service", 500, 850, "索引服务", [
                   ("query-responsibility", 522, 270, 252, 258, "查询处理", ["解析查询条件", "检索匹配条目", "生成候选结果"]),
                   ("update-responsibility", 799, 270, 252, 258, "索引更新", ["接收资料变更", "构建索引条目", "维护索引版本"]),
                   ("ranking-responsibility", 1076, 270, 252, 258, "结果排序", ["计算候选得分", "组织返回顺序", "输出排序结果"])])]
    for name, x, width, title, duties in modules:
        body.extend([f'<g id="{name}"><rect class="frame frame-inherited" x="{x}" y="146" width="{width}" height="406"/>',
                     text(x + 22, 184, title, "module-title"),
                     text(x + 22, 213, "内层模块 · 继承外层主色", "module-type"),
                     text(x + 22, 251, f"职责分区 · 均由{title}承担", "module-type")])
        for duty, dx, y, w, h, label, lines in duties:
            body.extend([f'<g id="{duty}"><rect class="duty" x="{dx}" y="{y}" width="{w}" height="{h}"/>',
                         f'<path class="duty-accent" d="M{dx+16},{y+22} h28"/>',
                         text(dx + 16, y + 55, label, "duty-title")])
            for i, line in enumerate(lines):
                body.append(text(dx + 16, y + (107 if len(lines) > 1 else 82) + i * 32, line, "duty-body"))
            body.append('</g>')
        body.append('</g>')
    body.append('</g>')
    links = [edge("submit-request", (374, 306), (500, 306), "plain", ("提交查询 / 更新",)),
             edge("return-result", (500, 454), (374, 454), "plain", ("返回结果 / 状态",))]
    key = legend([("plain", "模块间的请求与结果交接")],
                 [("module-retrieval", "资料检索系统及两个子模块；实线框表达模块边界"),
                  ("module-retrieval legend-duty", "所属模块的职责分区，同组职责统一填色")])
    return ("模块嵌套与职责分区（通用示例）", 610, body, [], links, key,
            "资料检索系统采用橙色。资料应用与索引服务具有各自的职责和协作边界，作为子模块展开并继承橙色。"
            "本例主要展示包含关系与职责归属，子模块使用白底，职责使用同一档较明显浅色；"
            "查询处理、索引更新和结果排序均由索引服务承担。组件与关系均为虚构示例。")


def palette():
    samples = []
    for i, (color, name) in enumerate((("gold", "琥珀金色"), ("orange", "橙色"), ("red", "红色"),
                                       ("blue", "蓝色"), ("purple", "紫色"), ("green", "绿色"), ("teal", "青色"))):
        x, y = 40 + (i % 2) * 680, 32 + (i // 2) * 220
        samples.extend([f'<g id="palette-{color}" style="--module-color:var(--{color});--module-bg:var(--{color}-bg);--module-chip:var(--{color}-chip)">',
                        f'<rect class="frame" x="{x}" y="{y}" width="640" height="190"/>',
                        text(x + 20, y + 32, "示例模块", "frame-title"),
                        text(x + 620, y + 32, name, "note", 'text-anchor="end"')])
        for dx, style, title in ((20, "card", "内部组件"), (328, "duty", "职责分区")):
            samples.extend([f'<rect class="{style}" x="{x+dx}" y="{y+58}" width="292" height="108"/>',
                            text(x + dx + 16, y + 85, title, "node-title"),
                            text(x + dx + 16, y + 113, "处理请求，返回结果", "body-text"),
                            text(x + dx + 16, y + 141, "补充说明：同组统一样式")])
        samples.append('</g>')
    key = legend([], [("module-retrieval", "浅底与主色边框：模块身份，内部组件使用统一卡片背景"),
                      ("module-retrieval legend-duty", "同色系较明显浅底：模块内部职责，同组使用统一填色")])
    return ("固定色板与填色层次（校准示例）", 914, samples, [], [], key,
            "各色使用相同面积、文字和层次，仅用于比较视觉强度，不分配实际模块。"
            "按实际显示尺寸检查浅底、内部组件与职责分区，并分别复看浅色、深色和灰度效果。")


LAYOUTS = {"layered": layered, "parallel": parallel, "loop": loop, "scenario": scenario, "nested": nested, "palette": palette}


def render(layout):
    template = (PACKAGE / "assets/architecture-template.html").read_text(encoding="utf-8")
    title, height, backgrounds, nodes, links, key, caption = LAYOUTS[layout]()
    defs = re.search(r"<defs>.*?</defs>", template, re.S).group()
    # 独立配色组件使用浅底，继承配色的内部组件保留统一卡片背景。
    content = "\n".join([*backgrounds, *links,
                         *(card(n, tinted=layout in {"parallel", "loop"},
                                module_title=n[0] in {"analysis", "review", "request", "execute", "gate"}) for n in nodes)])
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" class="architecture" viewBox="0 0 1400 {height}" role="img" aria-labelledby="sample-title" aria-describedby="sample-description">'
           f'<title id="sample-title">{escape(title)}</title><desc id="sample-description">{escape(caption)}</desc>\n{defs}\n{content}\n</svg>')
    output = re.sub(r"<svg\b.*?</svg>", lambda _: svg, template, count=1, flags=re.S)
    output = re.sub(r"<title>.*?</title>", lambda _: f"<title>{escape(title)}</title>", output, count=1)
    output = re.sub(r"<h1>.*?</h1>", lambda _: f"<h1>{escape(title)}</h1>", output, count=1)
    output = re.sub(r'<div class="legend".*?(?=\s*</main>)', lambda _: key, output, count=1, flags=re.S)
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
