#!/usr/bin/env python3
"""skillctl：跨 Agent、跨机器管理从 GitHub 拉取的 skill。

清单是工作 clone 根目录的 skills.json，记录装哪些 skill、叫什么名字。
skill 实体装在 ~/.agents/skills/<安装名>/（Codex 读取），
~/.claude/skills/<安装名> 是指向它的软链接（Claude Code 读取）。
上游仓库 clone 在 ~/.local/share/agent-skills/repos/<owner>/<repo>/。

只依赖 git 和 Python 3.9 标准库。

环境变量（测试用）：
  SKILLCTL_GIT_BASE   上游仓库地址前缀，默认 https://github.com/
  SKILLCTL_FORCE_TTY  设为 1 时把标准输入当作终端，走交互流程
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

VERSION = 1
MARKER = ".skillctl.json"
# 复制和计算哈希时都跳过；node_modules 体积大且和本机环境绑定
IGNORED = {".git", ".DS_Store", "node_modules"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

# 静态保留名。Codex 自带的 skill 名在运行时从 ~/.codex/skills/.system/ 读取。
RESERVED_GENERIC = {
    "review", "qa", "ship", "spec", "learn", "health",
    "tdd", "research", "triage", "teach", "code-review", "retro",
}
RESERVED_CLAUDE_SKILLS = {
    "batch", "claude-api", "dataviz", "debug", "design", "design-sync",
    "doctor", "fewer-permission-prompts", "loop", "run", "run-skill-generator",
    "simplify", "update-config", "verify", "workflow-authoring",
    "checkup", "proactive",
}
RESERVED_CLAUDE_COMMANDS = {"init", "schedule", "security-review"}

SCRIPT = Path(__file__).resolve()
WORK = SCRIPT.parent.parent
MANIFEST = WORK / "skills.json"

HOME = Path.home()
DATA = HOME / ".local" / "share" / "agent-skills"
REPOS = DATA / "repos"
AGENTS_DIR = HOME / ".agents" / "skills"
CLAUDE_DIR = HOME / ".claude" / "skills"
CODEX_DIR = HOME / ".codex" / "skills"
CODEX_SYSTEM = CODEX_DIR / ".system"
BIN_LINK = HOME / ".local" / "bin" / "skillctl"

GIT_BASE = os.environ.get("SKILLCTL_GIT_BASE", "https://github.com/")
GIT_ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0")
GIT_ENV.setdefault("GIT_SSH_COMMAND", "ssh -o BatchMode=yes")


class SkillctlError(Exception):
    pass


# ---------- 通用 ----------

def say(msg=""):
    print(msg, flush=True)


def warn(msg):
    print(msg, file=sys.stderr, flush=True)


TZ = datetime.timezone(datetime.timedelta(hours=8))
EPOCH = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)


def now():
    """当前时间，固定用 UTC+8，精确到秒。"""
    return datetime.datetime.now(TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def stamp_of(entry):
    """把 updated_at 解析成带时区的时间，用于比较先后；无法解析的视为最早。"""
    text = (entry or {}).get("updated_at", "")
    try:
        t = datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return EPOCH
    return t if t.tzinfo else t.replace(tzinfo=TZ)


def git(args, cwd=None, check=True):
    proc = subprocess.run(
        ["git"] + args, cwd=cwd, env=GIT_ENV,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
    )
    if check and proc.returncode != 0:
        raise SkillctlError(f"git {' '.join(args)} 失败：{proc.stderr.strip()}")
    return proc


def write_atomic(path, text):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def is_tty():
    return os.environ.get("SKILLCTL_FORCE_TTY") == "1" or sys.stdin.isatty()


def ask(prompt):
    sys.stdout.write(prompt)
    sys.stdout.flush()
    line = sys.stdin.readline()
    if not line:
        raise SkillctlError("输入已结束，操作取消")
    return line.strip()


# ---------- 清单 ----------

def empty_manifest():
    return {"version": VERSION, "skills": {}}


def dump_manifest(data):
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def parse_manifest(text, source):
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise SkillctlError(f"{source} 不是合法的 JSON：{e}")
    if not isinstance(data, dict) or "version" not in data or not isinstance(data.get("skills"), dict):
        raise SkillctlError(f"{source} 不是 skillctl 清单：顶层缺少 version 或 skills")
    return data


def load_manifest(path=MANIFEST):
    if not path.exists():
        return empty_manifest()
    return parse_manifest(path.read_text(encoding="utf-8"), path)


def save_manifest(data, path=MANIFEST):
    write_atomic(path, dump_manifest(data))


def merge_manifests(local, other):
    """按 skill 标识逐条合并，取 updated_at 较晚的整条；时间相同保留本机。

    返回合并结果和被另一份覆盖的标识列表。
    """
    merged = {"version": VERSION, "skills": dict(local["skills"])}
    changed = []
    for sid, entry in other["skills"].items():
        mine = merged["skills"].get(sid)
        if mine is None or stamp_of(entry) > stamp_of(mine):
            if mine != entry:
                changed.append(sid)
            merged["skills"][sid] = entry
    return merged, changed


def split_id(sid):
    repo, _, path = sid.partition(":")
    if not REPO_RE.match(repo) or not path:
        raise SkillctlError(f"无效的 skill 标识：{sid}")
    return repo, path


def present(manifest):
    return {sid: e for sid, e in manifest["skills"].items() if e.get("state") == "present"}


def describe_change(sid, old, new):
    name = new.get("name")
    if new.get("state") == "removed":
        return f"删除 {old.get('name', name) if old else name}（{sid}）"
    if not old or old.get("state") != "present":
        return f"新增 {name}（{sid}）"
    if old.get("name") != name:
        return f"改名 {old.get('name')} → {name}（{sid}）"
    return f"更新 {name}（{sid}）"


# ---------- 工作 clone ----------

def git_dir():
    out = git(["rev-parse", "--git-dir"], cwd=WORK, check=False)
    if out.returncode != 0:
        return None
    p = Path(out.stdout.strip())
    return p if p.is_absolute() else WORK / p


def pending_path():
    d = git_dir()
    return d / "skillctl-pending.json" if d else None


def recover_pending():
    pending = pending_path()
    if not pending or not pending.exists():
        return
    other = parse_manifest(pending.read_text(encoding="utf-8"), pending)
    merged, _ = merge_manifests(load_manifest(), other)
    save_manifest(merged)
    pending.unlink()
    say("已合并上次中断遗留的清单临时文件")


def upstream_ref():
    out = git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], cwd=WORK, check=False)
    return out.stdout.strip() if out.returncode == 0 else None


def pull_work():
    """拉取工作 clone：合并远端清单与本地未提交修改，再快进。"""
    if git_dir() is None:
        warn(f"提示：{WORK} 不是 git 仓库，跳过拉取")
        return
    recover_pending()
    fetch = git(["fetch", "--quiet"], cwd=WORK, check=False)
    if fetch.returncode != 0:
        warn(f"提示：工作 clone 拉取失败，继续使用本地清单（{fetch.stderr.strip()}）")
        return
    up = upstream_ref()
    if not up:
        warn("提示：工作 clone 当前分支没有上游分支，跳过拉取")
        return
    behind = int(git(["rev-list", "--count", f"HEAD..{up}"], cwd=WORK).stdout.strip() or 0)
    if behind == 0:
        return

    remote_text = git(["show", f"{up}:skills.json"], cwd=WORK, check=False)
    remote = parse_manifest(remote_text.stdout, f"{up}:skills.json") if remote_text.returncode == 0 else empty_manifest()
    merged, _ = merge_manifests(load_manifest(), remote)
    pending = pending_path()
    write_atomic(pending, dump_manifest(merged))

    tracked = git(["cat-file", "-e", "HEAD:skills.json"], cwd=WORK, check=False).returncode == 0
    if tracked:
        git(["checkout", "--", "skills.json"], cwd=WORK)
    elif MANIFEST.exists():
        MANIFEST.unlink()
    ff = git(["merge", "--ff-only", "--quiet", up], cwd=WORK, check=False)
    os.replace(pending, MANIFEST)
    if ff.returncode != 0:
        warn(f"工作 clone 无法快进，仓库保持不动，清单已合并远端内容：{ff.stderr.strip()}")
    else:
        say(f"工作 clone 已快进 {behind} 个提交")


# ---------- skill 文件 ----------

def read_frontmatter(skill_md):
    """返回 (name, 描述第一行)。"""
    try:
        text = skill_md.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return "", ""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return "", ""
    name, desc = "", ""
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            break
        m = re.match(r"^name:\s*(.*)$", line)
        if m and not name:
            name = m.group(1).strip().strip("'\"")
        m = re.match(r"^description:\s*(.*)$", line)
        if m and not desc:
            desc = m.group(1).strip().strip("'\"")
            if desc in ("", ">", "|", ">-", "|-"):
                for nxt in lines[i + 1:]:
                    if nxt.strip() and nxt.startswith((" ", "\t")):
                        desc = nxt.strip()
                        break
    return name, desc


def rewrite_name(skill_md, new_name):
    text = skill_md.read_text(encoding="utf-8")
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        lines = ["---", f"name: {new_name}", "---"] + lines
    else:
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        if end is None:
            raise SkillctlError(f"{skill_md} 的 frontmatter 没有结束标记")
        for i in range(1, end):
            if re.match(r"^name:", lines[i]):
                lines[i] = f"name: {new_name}"
                break
        else:
            lines.insert(1, f"name: {new_name}")
    skill_md.write_text("\n".join(lines), encoding="utf-8")


def content_hash(directory):
    h = hashlib.sha256()
    files = []
    for root, dirs, names in os.walk(directory):
        dirs[:] = sorted(d for d in dirs if d not in IGNORED)
        for n in names:
            if n in IGNORED or (root == str(directory) and n == MARKER):
                continue
            files.append(Path(root, n))
    for f in sorted(files, key=lambda p: p.relative_to(directory).as_posix()):
        rel = f.relative_to(directory).as_posix()
        h.update(rel.encode() + b"\0")
        h.update(f.read_bytes() if not f.is_symlink() else os.readlink(f).encode())
        h.update(b"\0")
    return h.hexdigest()


def read_marker(directory):
    f = directory / MARKER
    if directory.is_symlink() or not f.is_file():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def write_marker(directory, sid, commit):
    data = {"id": sid, "commit": commit, "hash": content_hash(directory)}
    (directory / MARKER).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def discover(repo_dir):
    """列出仓库里所有包含 SKILL.md 的目录，返回 [(路径, name, 描述)]。"""
    found = []
    for root, dirs, names in os.walk(repo_dir):
        dirs[:] = sorted(d for d in dirs if d not in (".git", "node_modules"))
        if "SKILL.md" in names:
            rel = Path(root).relative_to(repo_dir).as_posix()
            name, desc = read_frontmatter(Path(root, "SKILL.md"))
            found.append((rel if rel != "" else ".", name, desc))
    return sorted(found, key=lambda x: (x[0] != ".", x[0]))


def points_to(link, target):
    if not link.is_symlink():
        return False
    dest = Path(os.path.normpath(os.path.join(str(link.parent), os.readlink(link))))
    return dest == target


def remove_link_to(link, target):
    if points_to(link, target):
        link.unlink()


# ---------- 仓库副本 ----------

def repo_dir(repo):
    return REPOS / repo


def ensure_repo(repo):
    d = repo_dir(repo)
    if (d / ".git").exists():
        return d
    d.parent.mkdir(parents=True, exist_ok=True)
    say(f"clone {repo} …")
    git(["clone", "--quiet", f"{GIT_BASE}{repo}", str(d)])
    return d


def head(d):
    return git(["rev-parse", "HEAD"], cwd=d).stdout.strip()


# ---------- 名字 ----------

def reserved_names():
    names = RESERVED_GENERIC | RESERVED_CLAUDE_SKILLS | RESERVED_CLAUDE_COMMANDS
    if CODEX_SYSTEM.is_dir():
        names |= {p.name for p in CODEX_SYSTEM.iterdir() if (p / "SKILL.md").is_file()}
    return names


def scan_dirs():
    dirs = [AGENTS_DIR, CLAUDE_DIR, CODEX_DIR, CODEX_SYSTEM,
            Path.cwd() / ".agents" / "skills", Path.cwd() / ".claude" / "skills"]
    out, seen = [], set()
    for d in dirs:
        key = os.path.abspath(str(d))
        if key not in seen:
            seen.add(key)
            out.append(d)
    return out


def occupied(name, ignore_id=None):
    """扫描范围内是否已有同名目录；属于 ignore_id 自己安装的不算。"""
    for d in scan_dirs():
        p = d / name
        if not (p.exists() or p.is_symlink()):
            continue
        if d in (AGENTS_DIR, CLAUDE_DIR) and ignore_id:
            t = AGENTS_DIR / name
            mk = read_marker(t)
            if mk and mk.get("id") == ignore_id:
                continue
        return str(p)
    return None


def valid_name(name):
    return bool(name) and len(name) <= 64 and bool(NAME_RE.match(name))


def apply_prefix(prefix, base):
    if not prefix:
        return base
    if not prefix.endswith("-"):
        prefix += "-"
    return base if base.startswith(prefix) else prefix + base


def name_problem(name, manifest, sid, taken=()):
    if not valid_name(name):
        return "不符合命名规范（1 到 64 个小写字母、数字或单个连字符）"
    if name in reserved_names():
        return "是保留名"
    for other_id, e in present(manifest).items():
        if other_id != sid and e["name"] == name:
            return f"已被清单里的 {other_id} 使用"
    if name in taken:
        return "和本次选中的其他 skill 重名"
    where = occupied(name, ignore_id=sid)
    if where:
        return f"已有同名目录 {where}"
    return None


def parse_selection(text, count):
    picked = []
    for part in text.replace("，", ",").split(","):
        part = part.strip()
        if not part:
            continue
        m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", part)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            if lo > hi:
                lo, hi = hi, lo
            nums = range(lo, hi + 1)
        elif part.isdigit():
            nums = [int(part)]
        else:
            raise SkillctlError(f"无法识别：{part}")
        for n in nums:
            if not 1 <= n <= count:
                raise SkillctlError(f"编号超出范围：{n}")
            if n not in picked:
                picked.append(n)
    return picked


# ---------- 安装与卸载 ----------

class Report:
    def __init__(self):
        self.lines = []
        self.problems = 0

    def info(self, msg):
        self.lines.append(msg)
        say(msg)

    def problem(self, msg):
        self.problems += 1
        self.lines.append(msg)
        say(f"  ! {msg}")


def copy_skill(src, sid, name, commit):
    AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    tmp = AGENTS_DIR / f".skillctl-tmp-{name}"
    if tmp.exists():
        shutil.rmtree(tmp)
    shutil.copytree(str(src), str(tmp), ignore=shutil.ignore_patterns(*IGNORED),
                    ignore_dangling_symlinks=True)
    upstream_name, _ = read_frontmatter(tmp / "SKILL.md")
    if upstream_name != name:
        rewrite_name(tmp / "SKILL.md", name)
    write_marker(tmp, sid, commit)
    target = AGENTS_DIR / name
    if target.exists():
        shutil.rmtree(target)
    os.replace(tmp, target)


def ensure_claude_link(name, report):
    t, l = AGENTS_DIR / name, CLAUDE_DIR / name
    if points_to(l, t):
        return
    if l.exists() or l.is_symlink():
        report.problem(f"{name}：{l} 已被占用，没有建立指向 {t} 的软链接")
        return
    CLAUDE_DIR.mkdir(parents=True, exist_ok=True)
    l.symlink_to(t)


def install_entry(sid, entry, report):
    """让一个 present 条目在本机就位。返回是否做了改动。"""
    repo, path = split_id(sid)
    name = entry["name"]
    t = AGENTS_DIR / name
    try:
        rdir = ensure_repo(repo)
    except SkillctlError as e:
        report.problem(f"{name}：{e}")
        return False
    src = rdir if path == "." else rdir / path
    if not (src / "SKILL.md").is_file():
        report.problem(f"{name}：仓库副本当前提交里已没有 {path}/SKILL.md，保留已安装的版本")
        return False
    changed = False

    if entry.get("link"):
        if t.is_symlink():
            if not points_to(t, rdir):
                report.problem(f"{name}：{t} 指向别处，名字冲突")
                return False
        elif t.exists():
            report.problem(f"{name}：{t} 已存在且不是 skillctl 安装的，名字冲突")
            return False
        else:
            AGENTS_DIR.mkdir(parents=True, exist_ok=True)
            t.symlink_to(rdir)
            report.info(f"已链接 {name} → {rdir}")
            changed = True
    else:
        commit = head(rdir)
        if t.is_symlink() or (t.exists() and not t.is_dir()):
            report.problem(f"{name}：{t} 已被占用，名字冲突")
            return False
        if not t.exists():
            copy_skill(src, sid, name, commit)
            report.info(f"已安装 {name}（{sid}）")
            changed = True
        else:
            mk = read_marker(t)
            if not mk or mk.get("id") != sid:
                report.problem(f"{name}：{t} 不是这个条目安装的，名字冲突")
                return False
            if content_hash(t) != mk.get("hash"):
                report.problem(f"{name}：本地手改过，没有覆盖")
            elif mk.get("commit") != commit:
                copy_skill(src, sid, name, commit)
                report.info(f"已重装 {name} 到 {commit[:7]}")
                changed = True
    ensure_claude_link(name, report)
    return changed


def uninstall_dir(t, sid, name, report, reason):
    """删除 skillctl 安装的目录 t 及指向它的软链接；手改过的保留。"""
    if t.is_symlink():
        t.unlink()
        remove_link_to(CLAUDE_DIR / t.name, t)
        report.info(f"已{reason} {name}")
        return
    mk = read_marker(t)
    if not mk or mk.get("id") != sid:
        return
    if content_hash(t) != mk.get("hash"):
        report.problem(f"{t.name}：本地手改过，没有删除")
        return
    shutil.rmtree(t)
    remove_link_to(CLAUDE_DIR / t.name, t)
    report.info(f"已{reason} {t.name}")


def managed_dirs():
    """返回 {目录: skill 标识}，包括复制安装的目录和链接安装的软链接。"""
    out = {}
    if not AGENTS_DIR.is_dir():
        return out
    for p in AGENTS_DIR.iterdir():
        if p.name.startswith("."):
            continue
        if p.is_symlink():
            dest = Path(os.path.normpath(os.path.join(str(p.parent), os.readlink(p))))
            try:
                rel = dest.relative_to(REPOS).as_posix()
            except ValueError:
                continue
            if REPO_RE.match(rel):
                out[p] = f"{rel}:."
        else:
            mk = read_marker(p)
            if mk and mk.get("id"):
                out[p] = mk["id"]
    return out


def name_winners(manifest, report):
    groups = {}
    for sid, e in present(manifest).items():
        groups.setdefault(e["name"], []).append((stamp_of(e), sid))
    winners = {}
    for name, items in groups.items():
        items.sort()
        winners[items[0][1]] = manifest["skills"][items[0][1]]
        for _, sid in items[1:]:
            report.problem(f"清单里 {sid} 和 {items[0][1]} 都叫 {name}，跳过较晚的 {sid}，请用 add --as 改名")
    return winners


def reconcile(manifest, report):
    """让本机安装状态与清单一致。"""
    skills = manifest["skills"]
    # 1. removed 条目和改名后留下的旧目录
    for p, sid in managed_dirs().items():
        e = skills.get(sid)
        if e is None:
            report.problem(f"{p.name}：清单里没有对应条目（{sid}），只报告不删除")
        elif e.get("state") == "removed":
            uninstall_dir(p, sid, p.name, report, "卸载")
        elif e.get("name") != p.name:
            uninstall_dir(p, sid, p.name, report, "清理改名前的旧目录")
    # 2. present 条目
    for sid, e in sorted(name_winners(manifest, report).items()):
        install_entry(sid, e, report)


# ---------- 命令 ----------

def remind_readme():
    """清单变化后运行仓库自带的 README 校验，有漂移就提醒，不影响退出码。"""
    checker = WORK / "scripts" / "check-readme-sync.py"
    if not checker.is_file():
        return
    proc = subprocess.run([sys.executable, str(checker)], cwd=str(WORK),
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    if proc.returncode == 0:
        return
    drift = [l.strip() for l in proc.stdout.splitlines() if l.strip().startswith("[")]
    say("提示：README 和清单不一致，需要在主力机上补 README（用途和分类要人工写）：")
    for line in drift or proc.stdout.strip().splitlines():
        say(f"  {line}")


def ensure_bin_link():
    target = SCRIPT
    if BIN_LINK.is_symlink() or BIN_LINK.exists():
        if not points_to(BIN_LINK, target):
            warn(f"提示：{BIN_LINK} 已被占用，没有改成指向 {target}")
        return
    BIN_LINK.parent.mkdir(parents=True, exist_ok=True)
    BIN_LINK.symlink_to(target)
    say(f"已创建命令链接 {BIN_LINK} → {target}")
    if str(BIN_LINK.parent) not in os.environ.get("PATH", "").split(os.pathsep):
        warn(f"提示：{BIN_LINK.parent} 不在 PATH 里，把它加进 PATH 后才能直接运行 skillctl")


def cmd_sync(args=None):
    pull_work()
    manifest = load_manifest()
    report = Report()
    reconcile(manifest, report)
    if report.problems:
        say(f"sync 完成，{report.problems} 个问题需要处理")
    return 1 if report.problems else 0


def print_list(repo, skills, manifest, rdir, fresh):
    if not fresh:
        commit = git(["log", "-1", "--format=%h %cd", "--date=short"], cwd=rdir).stdout.strip()
        say(f"仓库副本停在 {commit}，要看上游最新内容先运行 skillctl update {repo}")
    installed = {split_id(sid)[1]: e["name"] for sid, e in present(manifest).items() if split_id(sid)[0] == repo}
    reserved = reserved_names()
    for i, (path, name, desc) in enumerate(skills, start=1):
        if path in installed:
            state = f"已装为 {installed[path]}"
        elif name in reserved:
            state = "保留名"
        elif occupied(name) or any(e["name"] == name for e in present(manifest).values()):
            state = "重名"
        else:
            state = ""
        say(f"{i:>3}. {name or '(无 name)'}  [{path}]  {state}")
        if desc:
            say(f"     {desc[:100]}")


def cmd_add(args):
    repo = args.repo
    if not REPO_RE.match(repo):
        raise SkillctlError("仓库要写成 owner/repo")
    if args.as_name and args.prefix:
        raise SkillctlError("--as 和 --prefix 不能同时使用")
    pull_work()
    manifest = load_manifest()
    report = Report()
    reconcile(manifest, report)

    fresh = not (repo_dir(repo) / ".git").exists()
    rdir = ensure_repo(repo)
    skills = discover(rdir)
    if not skills:
        raise SkillctlError(f"{repo} 里没有找到 SKILL.md")

    interactive = False
    if args.skill:
        wanted = [s.strip() for s in args.skill.split(",") if s.strip()]
        chosen = []
        for w in wanted:
            w = w.rstrip("/") or w
            hit = [s for s in skills if s[0] == w] or [s for s in skills if s[1] == w]
            if not hit:
                raise SkillctlError(f"{repo} 里没有 {w}，可选：" + "、".join(s[1] or s[0] for s in skills))
            if len(hit) > 1:
                raise SkillctlError(f"{repo} 里有多个叫 {w} 的 skill，请改用路径：" + "、".join(s[0] for s in hit))
            if hit[0] not in chosen:
                chosen.append(hit[0])
    else:
        print_list(repo, skills, manifest, rdir, fresh)
        if not is_tty():
            say("标准输入不是终端，没有安装任何 skill。用 --skill 指定要装的 skill")
            return 2
        if args.link:
            raise SkillctlError("--link 只能和 --skill 一起使用")
        interactive = True
        if len(skills) == 1:
            chosen = skills
        else:
            text = ask("输入要安装的编号（如 1,3,5-7），直接回车取消：")
            if not text:
                say("已取消")
                return 0
            chosen = [skills[n - 1] for n in parse_selection(text, len(skills))]
    if args.as_name and len(chosen) != 1:
        raise SkillctlError("--as 只能用于单个 skill")
    if args.link and len(chosen) != 1:
        raise SkillctlError("--link 只能用于单个 skill")

    existing = {split_id(sid)[1]: sid for sid in present(manifest) if split_id(sid)[0] == repo}
    prefix = args.prefix
    new_items = [c for c in chosen if c[0] not in existing]
    if interactive and not prefix and len(new_items) > 1:
        prefix = ask("统一前缀（如 gstack-），直接回车不加：")

    plan, taken, refused = [], [], 0
    for path, upstream, _ in chosen:
        sid = f"{repo}:{path}"
        if path in existing and not args.as_name:
            say(f"{upstream or path} 已装为 {manifest['skills'][sid]['name']}，不重复安装")
            continue
        if args.as_name:
            name = args.as_name
        elif not upstream:
            raise SkillctlError(f"{path} 的 SKILL.md 没有 name，用 --as 指定安装名")
        else:
            name = apply_prefix(prefix, upstream)
        problem = name_problem(name, manifest, sid, taken)
        while problem and interactive:
            alias = ask(f"{name} {problem}。输入别名，直接回车跳过：")
            if not alias:
                break
            name = alias
            problem = name_problem(name, manifest, sid, taken)
        if problem:
            report.problem(f"{name}：{problem}，没有安装")
            refused += 1
            continue
        taken.append(name)
        plan.append((sid, name))

    if not plan:
        return 1 if refused else 0
    if interactive:
        for sid, name in plan:
            say(f"  {name}  ←  {sid}")
        if ask("确认安装？[y/N] ").lower() not in ("y", "yes"):
            say("已取消")
            return 0

    stamp = now()
    for sid, name in plan:
        entry = {"name": name, "state": "present", "updated_at": stamp}
        if args.link:
            entry["link"] = True
        old = manifest["skills"].get(sid)
        if old and old.get("state") == "present" and old.get("link") and not args.link:
            entry["link"] = True
        manifest["skills"][sid] = entry
    save_manifest(manifest)
    reconcile(manifest, report)
    remind_readme()
    return 1 if (refused or report.problems) else 0


def cmd_remove(args):
    pull_work()
    manifest = load_manifest()
    hits = [sid for sid, e in present(manifest).items() if e["name"] == args.name]
    if not hits:
        raise SkillctlError(f"清单里没有叫 {args.name} 的 skill，不归 skillctl 管的 skill 不处理")
    stamp = now()
    for sid in hits:
        manifest["skills"][sid] = dict(manifest["skills"][sid], state="removed", updated_at=stamp)
    save_manifest(manifest)
    report = Report()
    reconcile(manifest, report)
    remind_readme()
    return 1 if report.problems else 0


def cmd_merge(args):
    pull_work()
    src = Path(args.file).expanduser()
    if not src.is_file():
        raise SkillctlError(f"找不到文件 {src}")
    other = parse_manifest(src.read_text(encoding="utf-8"), src)
    manifest = load_manifest()
    merged, changed = merge_manifests(manifest, other)
    if not changed:
        say("没有需要合并的改动")
    else:
        say(f"将合并以下 {len(changed)} 处改动：")
        for sid in sorted(changed):
            say("  " + describe_change(sid, manifest["skills"].get(sid), merged["skills"][sid]))
        if not args.yes:
            if not is_tty():
                say("标准输入不是终端，没有合并。确认无误后加 --yes 再运行")
                return 2
            if ask("确认合并并按清单安装、卸载？[y/N] ").lower() not in ("y", "yes"):
                say("已取消，清单和本机安装都没有改动")
                return 0
    save_manifest(merged)
    report = Report()
    reconcile(merged, report)
    if changed:
        remind_readme()
    return 1 if report.problems else 0


def cmd_update(args):
    pull_work()
    manifest = load_manifest()
    report = Report()
    reconcile(manifest, report)
    by_repo = {}
    for sid, e in present(manifest).items():
        by_repo.setdefault(split_id(sid)[0], []).append((sid, e))
    if args.repo:
        if args.repo not in by_repo:
            raise SkillctlError(f"清单里没有来自 {args.repo} 的 skill")
        by_repo = {args.repo: by_repo[args.repo]}

    for repo in sorted(by_repo):
        rdir = repo_dir(repo)
        if not (rdir / ".git").exists():
            continue
        fetch = git(["fetch", "--quiet"], cwd=rdir, check=False)
        if fetch.returncode != 0:
            report.problem(f"{repo}：拉取失败：{fetch.stderr.strip()}")
            continue
        old, new = head(rdir), git(["rev-parse", "origin/HEAD"], cwd=rdir).stdout.strip()
        if old == new:
            continue
        say(f"{repo}：{old[:7]} → {new[:7]}")
        changed_ids = set()
        for sid, e in sorted(by_repo[repo]):
            path = split_id(sid)[1]
            spec = [] if path == "." else ["--", path]
            files = git(["diff", "--name-only", old, new] + spec, cwd=rdir).stdout.split()
            if not files:
                continue
            changed_ids.add(sid)
            gone = git(["cat-file", "-e", f"{new}:{'' if path == '.' else path + '/'}SKILL.md"],
                       cwd=rdir, check=False).returncode != 0
            say(f"  {e['name']}：{len(files)} 个文件有变化" + ("，上游已删除这个 skill" if gone else ""))
            for f in files[:10]:
                say(f"    {f}")
            if len(files) > 10:
                say(f"    …另有 {len(files) - 10} 个")
        git(["reset", "--hard", "--quiet", new], cwd=rdir)
        for sid, e in by_repo[repo]:
            t = AGENTS_DIR / e["name"]
            mk = read_marker(t)
            if sid in changed_ids or e.get("link") or not mk or mk.get("id") != sid:
                install_entry(sid, e, report)
            elif content_hash(t) == mk.get("hash"):
                write_marker(t, sid, new)
    return 1 if report.problems else 0


def cmd_list(args):
    manifest = load_manifest()
    rows = []
    for sid, e in sorted(present(manifest).items(), key=lambda x: x[1]["name"]):
        t = AGENTS_DIR / e["name"]
        if e.get("link"):
            state = "链接" if t.is_symlink() else "未安装"
            commit = ""
            rdir = repo_dir(split_id(sid)[0])
            if (rdir / ".git").exists():
                commit = head(rdir)[:7]
        else:
            mk = read_marker(t)
            if not mk or mk.get("id") != sid:
                state, commit = ("未安装" if not t.exists() else "冲突"), ""
            else:
                commit = mk.get("commit", "")[:7]
                state = "正常" if content_hash(t) == mk.get("hash") else "本地手改"
        rows.append((e["name"], sid, commit, state))
    width = max((len(r[0]) for r in rows), default=4)
    for name, sid, commit, state in rows:
        say(f"{name:<{width}}  {commit:<7}  {state:<4}  {sid}")
    say(f"共 {len(rows)} 个")

    extra = unmanaged_skills()
    if extra:
        say()
        say(f"未托管的 skill（{len(extra)} 个，skillctl 不会改动它们）：")
        width = max(len(n) for n in extra)
        for name, (where, detail, hint) in sorted(extra.items()):
            say(f"{name:<{width}}  {where}  {detail}".rstrip())
            if hint:
                say(f"{'':<{width}}  纳入管理：先把现有目录移到备份，再运行 {hint}")
    return 0


def openskills_source(directory):
    """从 openskills 留下的 .openskills.json 读出 (owner/repo, 仓库内路径)。"""
    f = directory / ".openskills.json"
    if not f.is_file():
        return None
    try:
        meta = json.loads(f.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    m = re.search(r"github\.com[/:]([^/\s]+)/([^/\s#]+?)(?:\.git)?/?$", meta.get("repoUrl") or "")
    if not m:
        return None
    return f"{m.group(1)}/{m.group(2)}", (meta.get("subpath") or "").strip("/") or "."


def unmanaged_skills():
    """列出两个全局目录里不归 skillctl 管的 skill。

    返回 {名字: (所在目录, 说明, 建议的 add 命令或 None)}。
    """
    managed = set(managed_dirs())
    found = {}
    for label, base in (("~/.agents/skills", AGENTS_DIR), ("~/.claude/skills", CLAUDE_DIR)):
        if not base.is_dir():
            continue
        for p in sorted(base.iterdir()):
            if p.name.startswith(".") or not (p / "SKILL.md").is_file():
                continue
            if p in managed or any(points_to(p, t) for t in managed):
                continue
            found.setdefault(p.name, []).append((label, p))
    out = {}
    for name, items in found.items():
        where = "、".join(label for label, _ in items)
        detail, hint = "", None
        for _, p in items:
            src = openskills_source(p)
            if src:
                detail = f"来源 {src[0]}:{src[1]}"
                hint = f"skillctl add {src[0]} --skill {src[1]}"
                break
        if not detail:
            links = sorted({os.readlink(str(p)) for _, p in items if p.is_symlink()})
            detail = f"软链到 {'、'.join(links)}" if links else "来源未知"
        out[name] = (where, detail, hint)
    return out


def check_issues():
    issues = []
    # 工作 clone
    if git_dir() is not None:
        if pending_path().exists():
            issues.append("工作 clone 里有中断遗留的清单临时文件，运行 skillctl sync 合并")
        if git(["fetch", "--quiet"], cwd=WORK, check=False).returncode != 0:
            issues.append("工作 clone 拉取失败，无法判断是否落后远端")
        up = upstream_ref()
        if up:
            counts = git(["rev-list", "--left-right", "--count", f"HEAD...{up}"], cwd=WORK).stdout.split()
            ahead, behind = int(counts[0]), int(counts[1])
            if behind:
                issues.append(f"工作 clone 落后远端 {behind} 个提交，运行 skillctl sync")
            if ahead:
                issues.append(f"工作 clone 有 {ahead} 个本地提交还没推送")
        if git(["status", "--porcelain", "--", "skills.json"], cwd=WORK).stdout.strip():
            issues.append("skills.json 有未提交的修改（主力机：还没提交推送；副机：还有改动没传回主力机）")

    # 清单与安装状态
    manifest = load_manifest()
    names = {}
    for sid, e in present(manifest).items():
        names.setdefault(e["name"], []).append(sid)
    for name, sids in names.items():
        if len(sids) > 1:
            issues.append(f"清单里 {'、'.join(sids)} 都叫 {name}")
    for sid, e in present(manifest).items():
        name = e["name"]
        t, l = AGENTS_DIR / name, CLAUDE_DIR / name
        rdir = repo_dir(split_id(sid)[0])
        if e.get("link"):
            if not points_to(t, rdir):
                issues.append(f"{name}：没有按清单链接安装，运行 skillctl sync")
        else:
            mk = read_marker(t)
            if not t.exists():
                issues.append(f"{name}：未安装，运行 skillctl sync")
            elif not mk or mk.get("id") != sid:
                issues.append(f"{name}：{t} 不是这个条目安装的，名字冲突")
            elif content_hash(t) != mk.get("hash"):
                issues.append(f"{name}：本地手改过")
            elif (rdir / ".git").exists() and mk.get("commit") != head(rdir):
                issues.append(f"{name}：安装的提交和仓库副本不一致，运行 skillctl sync")
        if t.exists() and not points_to(l, t):
            issues.append(f"{name}：{l} 没有指向 {t}")
    for p, sid in managed_dirs().items():
        e = manifest["skills"].get(sid)
        if e is None:
            issues.append(f"{p.name}：清单里没有对应条目（{sid}）")
        elif e.get("state") == "removed" or e.get("name") != p.name:
            issues.append(f"{p.name}：清单里已删除或改名，运行 skillctl sync")

    # 名字冲突、失效软链接、目录名与 name 不一致
    groups = {}
    for d in scan_dirs():
        if not d.is_dir():
            continue
        for p in sorted(d.iterdir()):
            if p.name.startswith("."):
                continue
            if p.is_symlink() and not p.exists():
                issues.append(f"失效的软链接：{p}")
                continue
            if not (p / "SKILL.md").is_file():
                continue
            groups.setdefault(p.name, []).append(p)
            fm_name, _ = read_frontmatter(p / "SKILL.md")
            if fm_name and fm_name != p.name:
                issues.append(f"{p}：目录名和 name（{fm_name}）不一致")
    for name, paths in sorted(groups.items()):
        distinct = {}
        for p in paths:
            real = os.path.realpath(str(p))
            if real not in distinct:
                distinct[real] = content_hash(Path(real))
        if len(set(distinct.values())) > 1:
            issues.append(f"名字冲突 {name}：" + "、".join(str(p) for p in paths))

    # 上游更新
    for repo in sorted({split_id(sid)[0] for sid in present(manifest)}):
        rdir = repo_dir(repo)
        if not (rdir / ".git").exists():
            continue
        if git(["fetch", "--quiet"], cwd=rdir, check=False).returncode != 0:
            issues.append(f"{repo}：拉取失败，无法判断上游是否有更新")
            continue
        if head(rdir) != git(["rev-parse", "origin/HEAD"], cwd=rdir).stdout.strip():
            issues.append(f"{repo}：上游有更新，可运行 skillctl update {repo}")
    return issues


def cmd_check(args):
    issues = check_issues()
    for i in issues:
        say(f"  ! {i}")
    say(f"发现 {len(issues)} 个问题" if issues else "检查通过")
    return 1 if issues else 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="skillctl", description="跨 Agent、跨机器管理 skill")
    sub = parser.add_subparsers(dest="command")
    p = sub.add_parser("add", help="从 GitHub 仓库挑选并安装 skill")
    p.add_argument("repo", help="owner/repo")
    p.add_argument("--skill", help="要装的 skill，按 name 或仓库内路径，逗号分隔")
    p.add_argument("--as", dest="as_name", help="安装名，只能用于单个 skill；对已装的 skill 使用即改名")
    p.add_argument("--prefix", help="给这次新装的 skill 统一加前缀")
    p.add_argument("--link", action="store_true", help="把仓库副本根目录直接软链成 skill 目录")
    p = sub.add_parser("remove", help="卸载 skill 并在清单里标记为已删除")
    p.add_argument("name", help="安装名")
    sub.add_parser("sync", help="拉取工作 clone、合并清单，并让本机安装与清单一致")
    p = sub.add_parser("merge", help="把另一台的清单合并进来")
    p.add_argument("file")
    p.add_argument("-y", "--yes", action="store_true", help="跳过确认，直接合并")
    p = sub.add_parser("update", help="拉取上游并重装有变化的 skill")
    p.add_argument("repo", nargs="?")
    sub.add_parser("list", help="列出托管的 skill")
    sub.add_parser("check", help="只读检查")
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0
    handlers = {"add": cmd_add, "remove": cmd_remove, "sync": cmd_sync, "merge": cmd_merge,
                "update": cmd_update, "list": cmd_list, "check": cmd_check}
    try:
        ensure_bin_link()
        return handlers[args.command](args)
    except SkillctlError as e:
        warn(f"错误：{e}")
        return 1
    except KeyboardInterrupt:
        warn("已中断")
        return 130


if __name__ == "__main__":
    sys.exit(main())
