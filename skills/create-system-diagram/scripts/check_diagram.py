#!/usr/bin/env python3
"""Read-only checks for explicit-coordinate HTML/SVG architecture diagrams."""
import argparse
from collections import Counter
import itertools
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET


NUMBER = r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?"


def numbers(value):
    if re.sub(NUMBER, "", value).strip(" ,\t\r\n"):
        raise ValueError("需要显式数字坐标")
    result = [float(n) for n in re.findall(NUMBER, value)]
    if not all(math.isfinite(n) for n in result):
        raise ValueError("坐标必须为有限数值")
    return result


def points(element):
    tag = element.tag.rsplit("}", 1)[-1]
    if tag == "line":
        result = [(float(element.get("x1", 0)), float(element.get("y1", 0))),
                  (float(element.get("x2", 0)), float(element.get("y2", 0)))]
    elif tag == "polyline":
        values = numbers(element.get("points", ""))
        if len(values) % 2:
            raise ValueError("polyline 坐标须成对")
        result = list(zip(values[::2], values[1::2]))
    elif tag == "path":
        data = element.get("d", "")
        if re.sub(r"[MLHV,\s]|" + NUMBER, "", data):
            raise ValueError("只检查绝对 M/L/H/V 路径；曲线和相对路径需渲染复核")
        result = []
        for command, raw in re.findall(r"([MLHV])([^MLHV]*)", data):
            values = numbers(raw)
            if not result and command != "M":
                raise ValueError("路径须以 M 开始")
            if command in "ML":
                if len(values) % 2 or (command == "M" and result):
                    raise ValueError("只检查单段连续路径；坐标须成对")
                result.extend(zip(values[::2], values[1::2]))
            else:
                for value in values:
                    x, y = result[-1]
                    result.append((value, y) if command == "H" else (x, value))
    else:
        raise ValueError("只检查 path、polyline 和 line 连线")
    if not all(math.isfinite(v) for point in result for v in point):
        raise ValueError("坐标必须为有限数值")
    if len(result) < 2 or any(a[0] != b[0] and a[1] != b[1] for a, b in zip(result, result[1:])):
        raise ValueError("需要至少两个点组成的正交连线")
    return result


def distance(point, a, b):
    x, y = point
    return math.hypot(x - max(min(x, max(a[0], b[0])), min(a[0], b[0])),
                      y - max(min(y, max(a[1], b[1])), min(a[1], b[1])))


def inside_segment(a, b, box):
    x, y, w, h = box
    if a[0] == b[0]:
        return x < a[0] < x + w and max(min(a[1], b[1]), y) < min(max(a[1], b[1]), y + h)
    return y < a[1] < y + h and max(min(a[0], b[0]), x) < min(max(a[0], b[0]), x + w)


def check(source, min_entry=18, max_label_distance=48):
    issues, roots = [], []
    coverage = {"svgs": 0, "edges": 0, "checked_edges": 0, "checked_labels": 0, "skipped": 0}

    def report(code, path, message, fix, severity="error", **details):
        issues.append(dict(code=code, path=path, message=message, fix=fix, severity=severity, **details))

    # shortcut: 提取独立内嵌 SVG；需要检查嵌套 SVG 时改用完整 HTML/XML 解析。
    for i, markup in enumerate(re.findall(r"<svg\b.*?</svg\s*>", source, re.S), 1):
        try:
            roots.append(ET.fromstring(markup))
        except ET.ParseError as error:
            report("invalid_svg", f"svg[{i}]", str(error), "修正 SVG XML 结构后重试")
    if not roots:
        report("no_svg", "$", "未找到可解析的内嵌 SVG", "输入含完整 SVG 的 HTML 或独立 SVG")
    all_ids = Counter(e.get("id") for root in roots for e in root.iter() if e.get("id"))
    for name, count in all_ids.items():
        if count > 1:
            report("duplicate_id", f"#{name}", "文件内 ID 重复", "为每张图设置独立 ID 前缀并同步引用")

    for index, root in enumerate(roots, 1):
        prefix = f"svg[{index}]"
        coverage["svgs"] += 1
        parents = {child: parent for parent in root.iter() for child in parent}
        edges, boxes, labels = {}, {}, []

        def path(e):
            return f"{prefix}/#{e.get('id')}" if e.get("id") else f"{prefix}/{e.tag.rsplit('}', 1)[-1]}[{list(root.iter()).index(e)}]"

        def transformed(e):
            while e is not None:
                if e.get("transform") or "transform:" in e.get("style", "").replace(" ", ""):
                    return True
                e = parents.get(e)
            return False

        try:
            view = numbers(root.get("viewBox", ""))
            if len(view) != 4 or view[2] <= 0 or view[3] <= 0:
                raise ValueError("需要有效 viewBox")
        except ValueError as error:
            report("invalid_viewbox", prefix, str(error), "设置 min-x min-y width height")
            continue
        for e in root.iter():
            for ref in re.findall(r"url\(#([^)]*)\)", " ".join(e.attrib.values())) + e.get("aria-labelledby", "").split() + e.get("aria-describedby", "").split():
                if ref not in all_ids:
                    report("missing_reference", path(e), f"引用不存在：{ref}", "修正 marker 或可访问名称引用")
            classes = e.get("class", "").split()
            is_edge = "edge" in classes
            is_box = e.tag.rsplit("}", 1)[-1] == "rect" and bool(set(classes) & {"card", "mini"})
            is_label = e.tag.rsplit("}", 1)[-1] == "text" and "edge-label" in classes
            if is_edge:
                coverage["edges"] += 1
            if not (is_edge or is_box or is_label):
                continue
            if transformed(e):
                coverage["skipped"] += 1
                report("unsupported_transform", path(e), "变换后的几何未检查", "使用渲染后的坐标复核，不将本次结果视为完整检查", "warning")
                continue
            try:
                if is_edge:
                    route = points(e)
                    edges[e.get("id", path(e))] = (e, route)
                    coverage["checked_edges"] += 1
                    if any(not (view[0] <= x <= view[0] + view[2] and view[1] <= y <= view[1] + view[3]) for x, y in route):
                        report("edge_outside", path(e), "连线超出画布", "调整通道或画布范围")
                    if e.get("marker-end") and len(route) > 2 and math.dist(route[-2], route[-1]) < min_entry:
                        report("short_entry", path(e), "箭头前的末段过短", "调整接入侧或通道，给箭头留出清楚的直线段", "warning", length=math.dist(route[-2], route[-1]))
                elif is_box:
                    box = tuple(float(e.get(k, 0)) for k in ("x", "y", "width", "height"))
                    if not all(math.isfinite(v) for v in box) or min(box[2:]) <= 0:
                        raise ValueError("卡片尺寸无效")
                    boxes[path(e)] = box
                    x, y, w, h = box
                    if not (view[0] <= x and view[1] <= y and x + w <= view[0] + view[2] and y + h <= view[1] + view[3]):
                        report("card_outside", path(e), "卡片超出画布", "调整卡片或画布范围")
                elif is_label:
                    labels.append(e)
            except (ValueError, IndexError) as error:
                coverage["skipped"] += 1
                report("unsupported_geometry", path(e), str(error), "改用支持的显式坐标或在实际渲染中检查", "warning")

        for (a, box), (b, other) in itertools.combinations(boxes.items(), 2):
            x, y, w, h = box
            u, v, p, q = other
            if max(x, u) < min(x + w, u + p) and max(y, v) < min(y + h, v + q):
                report("card_overlap", f"{a}, {b}", "组件卡片相互覆盖", "调整卡片位置；归属外框使用 frame")
        segments = [(name, a, b) for name, (_, route) in edges.items() for a, b in zip(route, route[1:]) if a != b]
        for name, a, b in segments:
            for node, box in boxes.items():
                if inside_segment(a, b, box):
                    report("edge_through_card", f"{prefix}/#{name}", f"连线穿过卡片 {node}", "从卡片边界连接并调整空白通道")
        for (first, a, b), (second, c, d) in itertools.combinations(segments, 2):
            if first == second:
                continue
            if a[1] == b[1] and c[0] == d[0]:
                h1, h2, v1, v2 = a, b, c, d
            elif a[0] == b[0] and c[1] == d[1]:
                h1, h2, v1, v2 = c, d, a, b
            else:
                axis = 0 if a[1] == b[1] else 1
                if a[1 - axis] == c[1 - axis] and max(min(a[axis], b[axis]), min(c[axis], d[axis])) < min(max(a[axis], b[axis]), max(c[axis], d[axis])):
                    report("edge_overlap", f"{prefix}/#{first},#{second}", "连线存在共线重叠", "核对是否有意共用通道；独立关系应分开走线", "warning")
                continue
            x, y = v1[0], h1[1]
            if min(h1[0], h2[0]) < x < max(h1[0], h2[0]) and min(v1[1], v2[1]) < y < max(v1[1], v2[1]):
                report("edge_crossing", f"{prefix}/#{first},#{second}", "两条连线内部交叉", "调整端口与通道；有意汇合应将交点设为各连线的端点", point=[x, y])

        for e in labels:
            name = e.get("data-edge-label")
            if not name:
                if e.get("data-legend") != "true":
                    coverage["skipped"] += 1
                    report("unbound_label", path(e), "标签未关联具体连线", "用 data-edge-label 指定连线 ID；图例使用 data-legend='true'", "warning")
                continue
            if name not in edges:
                report("missing_label_edge", path(e), f"标签对应连线不存在或未检查：{name}", "核对连线 ID 和几何支持范围")
                continue
            try:
                xy = (float(e.get("x", "")), float(e.get("y", "")))
                if not all(math.isfinite(v) for v in xy):
                    raise ValueError("非有限坐标")
            except ValueError:
                coverage["skipped"] += 1
                report("unsupported_label_position", path(e), "标签锚点不是显式单点坐标", "在实际渲染中检查 tspan 或 textPath 的位置", "warning")
                continue
            coverage["checked_labels"] += 1
            if not "".join(e.itertext()).strip():
                report("empty_label", path(e), "连线标签为空", "填写动作与对象，或删除不需要的标签")
            route = edges[name][1]
            nearest = min(distance(xy, a, b) for a, b in zip(route, route[1:]))
            if nearest > max_label_distance:
                report("distant_label", path(e), "标签锚点远离对应连线", "将标签整体移近对应线段，或扩大局部间距", "warning", distance=round(nearest, 1))
    return {"ok": not any(i["severity"] == "error" for i in issues), "issues": issues, "coverage": coverage,
            "manual_checks": ["真实文字边界、穿字、字号与字形回退", "标签含义、编号解释及标签归属是否易读", "箭头形状、分组背景避让、线段端点处的接触", "CSS 几何覆盖、嵌套 SVG 与浏览器宽窄屏显示"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--min-entry", type=float, default=18, help="末端折线长度提示阈值，SVG 单位")
    parser.add_argument("--max-label-distance", type=float, default=48, help="标签锚点距离提示阈值，SVG 单位")
    args = parser.parse_args()
    if not all(math.isfinite(v) and v > 0 for v in (args.min_entry, args.max_label_distance)):
        parser.error("距离阈值须为正的有限数值")
    try:
        result = check(args.input.read_text(encoding="utf-8"), args.min_entry, args.max_label_distance)
    except (OSError, UnicodeError) as error:
        result = {"ok": False, "issues": [{"severity": "error", "code": "input_error", "path": str(args.input), "message": str(error), "fix": "提供可读取的 UTF-8 HTML/SVG 文件"}]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
