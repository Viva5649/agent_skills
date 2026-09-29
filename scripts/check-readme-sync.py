#!/usr/bin/env python3
"""校验 README.md 与 skill 清单、本机项目级 skill 是否一致。

只读，不修改任何文件。发现漂移时逐条打印并以退出码 1 结束。

README 里的用途描述和分类分组是人工撰写的，本脚本不生成、不改写，
只负责把「名单、计数、源仓库、两个标记列」这些可机械推导的部分对齐，
把需要人写的那一行精确指出来。

全局层以仓库根目录 skills.json 里 present 的条目为准，加上不归 skillctl 管的
UNMANAGED，不扫描本机目录，所以这一层在哪台电脑上校验结果都一样。

环境变量：
  PAI_ROOT           personal_ai_infrastructure 仓库根，默认 ~/Desktop/personal_ai_infrastructure
"""

import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
README = REPO / "README.md"
SELF_DIR = REPO / "skills"
THIRD_PARTY = REPO / "third_party"
GITMODULES = REPO / ".gitmodules"
MANIFEST = REPO / "skills.json"

# 由其他工具安装、不归 skillctl 管的全局 skill，及其上游
UNMANAGED = {"agent-reach": "panniantong/agent-reach", "ego-browser": None}
PAI_ROOT = Path(os.environ.get("PAI_ROOT") or Path.home() / "Desktop" / "personal_ai_infrastructure")
PAI_DIR = PAI_ROOT / ".claude" / "skills"

# 自建 skill 的上游标记为「本仓库」，不参与 third_party 收录判定
OWN_REPOS = {"viva5649/agent_skills", "viva5649/clarify-skill"}

problems = []
notes = []


def fail(tag, msg):
    problems.append(f"[{tag}] {msg}")


# ---------- 通用解析 ----------

def norm_repo(text):
    """把 markdown 链接或裸 URL 归一成 owner/name，小写。"""
    m = re.search(r"github\.com/([^/\s)]+)/([^/\s)#]+)", text or "")
    if not m:
        return (text or "").strip().lower()
    owner, name = m.group(1), m.group(2)
    if name.endswith(".git"):
        name = name[:-4]
    return f"{owner}/{name}".lower()


def first_link(cell):
    m = re.search(r"\[[^\]]*\]\((https?://[^)]+)\)", cell or "")
    return m.group(1) if m else ""


def code_name(cell):
    m = re.fullmatch(r"`([A-Za-z0-9._-]+)`", (cell or "").strip())
    return m.group(1) if m else None


def slice_section(lines, prefix, level="## "):
    out, on = [], False
    for ln in lines:
        if ln.startswith(level) and not ln.startswith(level + "#"):
            on = ln.startswith(prefix)
            continue
        if on:
            out.append(ln)
    return out


def table_rows(lines):
    for ln in lines:
        ln = ln.strip()
        if not ln.startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip("|").split("|")]
        if cells and cells[0] and set(cells[0]) <= set(":- "):
            continue
        yield cells


def skills_in(directory):
    if not directory.is_dir():
        return None
    return {d.name for d in directory.iterdir() if d.is_dir() and (d / "SKILL.md").is_file()}


def load_global():
    """返回 {全局 skill 名: 上游 owner/name 或 None}；skills.json 不存在时返回 None。"""
    if not MANIFEST.is_file():
        return None
    try:
        skills = json.loads(MANIFEST.read_text(encoding="utf-8"))["skills"]
    except (json.JSONDecodeError, OSError, KeyError) as e:
        fail("清单", f"skills.json 读取失败：{e}")
        return None
    out = {e["name"]: sid.split(":", 1)[0].lower()
           for sid, e in skills.items() if e.get("state") == "present"}
    for name, repo in UNMANAGED.items():
        out.setdefault(name, repo)
    return out


def provenance(name):
    """返回该全局 skill 的上游 owner/name，未知时返回 None。"""
    return (global_skills or {}).get(name)


def report_set_diff(tag, actual, documented, annotate=None):
    for name in sorted(actual - documented):
        extra = f"，{annotate(name)}" if annotate else ""
        fail(tag, f"实际有 README 没有：{name}{extra}")
    for name in sorted(documented - actual):
        fail(tag, f"README 有实际没有：{name}")


# ---------- 载入 ----------

if not README.is_file():
    print(f"找不到 {README}", file=sys.stderr)
    raise SystemExit(2)

lines = README.read_text(encoding="utf-8").splitlines()
sec_self = slice_section(lines, "## 一、")
sec_global = slice_section(lines, "## 二、")
sec_pai = slice_section(lines, "## 三、")
sec_third = slice_section(lines, "## 四、")
sec_unaggregated = slice_section(sec_third, "### 尚未聚合", level="### ")

submodule_repos = {
    norm_repo(m.group(1))
    for m in re.finditer(r"^\s*url\s*=\s*(\S+)", GITMODULES.read_text(encoding="utf-8"), re.M)
} if GITMODULES.is_file() else set()

actual_self = skills_in(SELF_DIR) or set()
global_skills = load_global()
actual_global = set(global_skills) if global_skills is not None else None
actual_pai = skills_in(PAI_DIR)

# ---------- 1. 三层名单 ----------

readme_self = {n for c in table_rows(sec_self) if (n := code_name(c[0]))}
report_set_diff("自建层", actual_self, readme_self)

if actual_global is None:
    notes.append(f"找不到 {MANIFEST}，跳过全局层校验")
    readme_global = set()
else:
    readme_global = {n for c in table_rows(sec_global) if (n := code_name(c[0]))}
    report_set_diff(
        "全局层", actual_global, readme_global,
        annotate=lambda n: f"源 {provenance(n) or '未知'}",
    )

if actual_pai is None:
    notes.append(f"pai 仓库不存在，跳过项目层校验：{PAI_DIR}")
else:
    readme_pai = {n for c in table_rows(sec_pai) if (n := code_name(c[0]))}
    report_set_diff("项目层", actual_pai, readme_pai)

# ---------- 2. 头部计数 ----------

head = "\n".join(lines[:20])
actual_third_total = len(list(THIRD_PARTY.glob("*/**/SKILL.md"))) if THIRD_PARTY.is_dir() else 0
actual_third_repos = len([d for d in THIRD_PARTY.iterdir() if d.is_dir()]) if THIRD_PARTY.is_dir() else 0

counts = [
    ("自建 skill", r"- 自建 skill：(\d+) 个", len(actual_self)),
    ("外部聚合仓库数", r"- 外部聚合：(\d+) 个仓库", actual_third_repos),
    ("外部聚合 skill 数", r"- 外部聚合：\d+ 个仓库，共 (\d+) 个 skill", actual_third_total),
]
if actual_global is not None:
    counts.append(("全局安装", r"- 全局安装：(\d+) 个", len(actual_global)))
if actual_pai is not None:
    counts.append(("项目级", r"- 项目级：(\d+) 个", len(actual_pai)))

for label, pattern, real in counts:
    m = re.search(pattern, head)
    if not m:
        fail("计数", f"头部读不到「{label}」这一行")
    elif int(m.group(1)) != real:
        fail("计数", f"头部「{label}」写 {m.group(1)}，实际 {real}")

# ---------- 3. third_party 每仓库 skill 数 ----------

for cells in table_rows(sec_third):
    name = code_name(cells[0])
    if not name or len(cells) < 3 or not cells[2].isdigit():
        continue
    d = THIRD_PARTY / name
    if not d.is_dir():
        fail("third_party", f"README 列了 {name}，但 third_party/ 下没有")
        continue
    real = len(list(d.glob("**/SKILL.md")))
    if real == 0:
        fail("third_party", f"{name} 里一个 SKILL.md 都没有，submodule 可能没初始化")
    elif real != int(cells[2]):
        fail("third_party", f"{name}：README 写 {cells[2]}，实际 {real}")

for d in sorted(THIRD_PARTY.iterdir()) if THIRD_PARTY.is_dir() else []:
    if d.is_dir() and not any(code_name(c[0]) == d.name for c in table_rows(sec_third)):
        fail("third_party", f"third_party/{d.name} 存在，但 README 第四节没有这一行")

# ---------- 4. 全局层的源仓库与「third_party/ 收录」列 ----------

unaggregated_expected = {}

if actual_global is not None:
    for cells in table_rows(sec_global):
        name = code_name(cells[0])
        if not name or len(cells) < 4:
            continue
        doc_repo = norm_repo(first_link(cells[2]))
        real_repo = provenance(name)
        if real_repo and doc_repo and real_repo != doc_repo:
            fail("源仓库", f"{name}：README 写 {doc_repo}，skills.json 是 {real_repo}")

        mark = cells[3].strip()
        if doc_repo in OWN_REPOS:
            expected = "本仓库"
        elif doc_repo in submodule_repos:
            expected = "✅"
        else:
            expected = "❌"
            unaggregated_expected.setdefault(doc_repo, []).append(name)
        if mark != expected:
            fail("收录列", f"{name}：README 写「{mark}」，按 .gitmodules 应为「{expected}」")

# ---------- 5. 自建层的「全局已装」列 ----------

if actual_global is not None:
    for cells in table_rows(sec_self):
        name = code_name(cells[0])
        if not name or len(cells) < 4:
            continue
        mark = cells[3].strip()
        expected = "✅" if name in actual_global else "❌"
        if mark != expected:
            fail("全局已装列", f"{name}：README 写「{mark}」，实际{'已' if expected == '✅' else '未'}安装")

# ---------- 6. 尚未聚合的上游仓库表 ----------

if actual_global is not None:
    documented_unagg = {
        norm_repo(first_link(c[0])) for c in table_rows(sec_unaggregated) if first_link(c[0])
    }
    for repo in sorted(set(unaggregated_expected) - documented_unagg):
        involved = "、".join(f"`{s}`" for s in sorted(unaggregated_expected[repo]))
        fail("尚未聚合表", f"缺 {repo}（涉及 {involved}）")
    for repo in sorted(documented_unagg - set(unaggregated_expected)):
        fail("尚未聚合表", f"多出 {repo}，已无对应的未收录 skill")

# ---------- 输出 ----------

for n in notes:
    print(f"提示：{n}")

if problems:
    print(f"\nREADME 同步校验发现 {len(problems)} 处漂移：\n")
    for p in problems:
        print(f"  {p}")
    print("\n用途描述和分类分组需人工撰写，脚本不自动改写 README。")
    raise SystemExit(1)

print("README 同步校验通过。")
