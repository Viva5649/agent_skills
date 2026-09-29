#!/usr/bin/env python3
"""skillctl：跨 Agent、跨机器管理从 GitHub 拉取的 skill。

清单是工作 clone 根目录的 skills.json，记录装哪些 skill、叫什么名字，
以及每个上游仓库用哪个提交（两台机器因此装同一版本）。
skill 实体装在 ~/.agents/skills/<安装名>/（Codex 读取），
~/.claude/skills/<安装名> 是指向它的软链接（Claude Code 读取）。
上游仓库浅 clone 在 ~/.local/share/agent-skills/repos/<owner>/<repo>/。

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
from concurrent.futures import ThreadPoolExecutor
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
# 网络卡住时尽快失败：SSH 连接和保活各给 15 秒；HTTPS 传输连续 30 秒低于 1KB/s 就放弃。
# 不设总时长上限，慢但仍在传的大仓库照样能 clone 完。
GIT_ENV.setdefault("GIT_SSH_COMMAND",
                   "ssh -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=15 -o ServerAliveCountMax=2")
GIT_OPTS = ["-c", "http.lowSpeedLimit=1000", "-c", "http.lowSpeedTime=30"]
LS_REMOTE_TIMEOUT = 30
NET_WORKERS = 16


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


def git(args, cwd=None, check=True, timeout=None):
    try:
        proc = subprocess.run(
            ["git"] + GIT_OPTS + args, cwd=cwd, env=GIT_ENV, timeout=timeout,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
        )
    except subprocess.TimeoutExpired:
        proc = subprocess.CompletedProcess(args, 124, "", f"timed out after {timeout}s")
    if check and proc.returncode != 0:
        raise SkillctlError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc


def run_parallel(fn, items):
    """对每个 item 并发执行 fn，返回 {item: (结果, SkillctlError 或 None)}。用于互不相干的网络操作。"""
    items = list(items)
    if not items:
        return {}
    with ThreadPoolExecutor(max_workers=min(NET_WORKERS, len(items))) as pool:
        futures = {item: pool.submit(fn, item) for item in items}
    out = {}
    for item, f in futures.items():
        try:
            out[item] = (f.result(), None)
        except SkillctlError as e:
            out[item] = (None, e)
    return out


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
        raise SkillctlError("input ended, cancelled")
    return line.strip()


# ---------- 清单 ----------

def empty_manifest():
    return {"version": VERSION, "skills": {}, "repos": {}}


def dump_manifest(data):
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def parse_manifest(text, source):
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise SkillctlError(f"{source} is not valid JSON: {e}")
    if not isinstance(data, dict) or "version" not in data or not isinstance(data.get("skills"), dict):
        raise SkillctlError(f"{source} is not a skillctl manifest: missing top-level version or skills")
    if not isinstance(data.setdefault("repos", {}), dict):
        raise SkillctlError(f"{source}: repos is not an object")
    return data


def load_manifest(path=MANIFEST):
    if not path.exists():
        return empty_manifest()
    return parse_manifest(path.read_text(encoding="utf-8"), path)


def save_manifest(data, path=MANIFEST):
    write_atomic(path, dump_manifest(data))


def merge_manifests(local, other):
    """skill 条目和仓库版本都逐条合并，取 updated_at 较晚的整条；时间相同保留本机。

    返回合并结果和被另一份覆盖的键列表：skill 标识带冒号，仓库名 owner/repo 不带。
    """
    merged = {"version": VERSION, "skills": dict(local["skills"]), "repos": dict(local.get("repos", {}))}
    changed = []
    for section in ("skills", "repos"):
        for key, entry in other.get(section, {}).items():
            mine = merged[section].get(key)
            if mine is None or stamp_of(entry) > stamp_of(mine):
                if mine != entry:
                    changed.append(key)
                merged[section][key] = entry
    return merged, changed


def split_id(sid):
    repo, _, path = sid.partition(":")
    if not REPO_RE.match(repo) or not path:
        raise SkillctlError(f"invalid skill id: {sid}")
    return repo, path


def present(manifest):
    return {sid: e for sid, e in manifest["skills"].items() if e.get("state") == "present"}


def repos_in_use(manifest):
    return {split_id(sid)[0] for sid in present(manifest)}


def pin_of(manifest, repo):
    return manifest.get("repos", {}).get(repo, {}).get("commit")


def set_pin(manifest, repo, commit, stamp=None):
    manifest.setdefault("repos", {})[repo] = {"commit": commit, "updated_at": stamp or now()}


def describe_change(sid, old, new):
    if ":" not in sid:
        if old and old.get("commit"):
            return f"{sid} version {old['commit'][:7]} -> {new['commit'][:7]}"
        return f"{sid} pinned at {new['commit'][:7]}"
    name = new.get("name")
    if new.get("state") == "removed":
        return f"remove {old.get('name', name) if old else name} ({sid})"
    if not old or old.get("state") != "present":
        return f"add {name} ({sid})"
    if old.get("name") != name:
        return f"rename {old.get('name')} -> {name} ({sid})"
    return f"update {name} ({sid})"


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
    say("Merged the pending manifest left by an interrupted run")


def upstream_ref():
    out = git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], cwd=WORK, check=False)
    return out.stdout.strip() if out.returncode == 0 else None


def pull_work():
    """拉取工作 clone：合并远端清单与本地未提交修改，再快进。"""
    if git_dir() is None:
        warn(f"Note: {WORK} is not a git repository, skipping pull")
        return
    recover_pending()
    fetch = git(["fetch", "--quiet"], cwd=WORK, check=False)
    if fetch.returncode != 0:
        warn(f"Note: failed to fetch the work clone, using the local manifest ({fetch.stderr.strip()})")
        return
    up = upstream_ref()
    if not up:
        warn("Note: the work clone's current branch has no upstream, skipping pull")
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
        warn(f"Cannot fast-forward the work clone, left it as is; the remote manifest was merged: {ff.stderr.strip()}")
    else:
        say(f"Fast-forwarded the work clone by {behind} commit(s)")


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
            raise SkillctlError(f"{skill_md}: frontmatter has no closing ---")
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
    """仓库副本不存在就浅 clone 默认分支的最新提交。"""
    d = repo_dir(repo)
    if (d / ".git").exists():
        return d
    d.parent.mkdir(parents=True, exist_ok=True)
    say(f"clone {repo} …")
    git(["clone", "--quiet", "--depth", "1", f"{GIT_BASE}{repo}", str(d)])
    return d


def head(d):
    return git(["rev-parse", "HEAD"], cwd=d).stdout.strip()


def has_commit(d, commit):
    return git(["cat-file", "-e", f"{commit}^{{commit}}"], cwd=d, check=False).returncode == 0


def checkout(d, commit):
    """把仓库副本切到指定提交，本地缺这个提交就只拉它一个。"""
    if head(d) == commit:
        return
    if git(["status", "--porcelain", "--untracked-files=no"], cwd=d).stdout.strip():
        raise SkillctlError(f"repo copy {d} has local changes, not switching to {commit[:7]}")
    if not has_commit(d, commit):
        git(["fetch", "--quiet", "--depth", "1", "origin", commit], cwd=d, check=False)
    if not has_commit(d, commit):
        raise SkillctlError(f"cannot fetch commit {commit[:7]}: network down or upstream history rewritten")
    git(["reset", "--hard", "--quiet", commit], cwd=d)


def fetch_latest(d):
    """拉取默认分支的最新提交，返回它的哈希，不切换。"""
    fetch = git(["fetch", "--quiet", "--depth", "1", "origin"], cwd=d, check=False)
    if fetch.returncode != 0:
        raise SkillctlError(f"fetch failed: {fetch.stderr.strip()}")
    return git(["rev-parse", "origin/HEAD"], cwd=d).stdout.strip()


def prepare_repo(manifest, repo, report):
    """让仓库副本停在清单记录的提交；清单没记录时记下副本当前的提交。"""
    try:
        d = ensure_repo(repo)
        pin = pin_of(manifest, repo)
        if pin:
            checkout(d, pin)
        else:
            set_pin(manifest, repo, head(d))
        return True
    except SkillctlError as e:
        report.problem(f"{repo}: {e}")
        return False


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
        return "breaks the naming rules (1-64 lowercase letters, digits, or single hyphens)"
    if name in reserved_names():
        return "is a reserved name"
    for other_id, e in present(manifest).items():
        if other_id != sid and e["name"] == name:
            return f"is already used by {other_id} in the manifest"
    if name in taken:
        return "clashes with another skill selected in this run"
    where = occupied(name, ignore_id=sid)
    if where:
        return f"clashes with existing directory {where}"
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
            raise SkillctlError(f"cannot parse: {part}")
        for n in nums:
            if not 1 <= n <= count:
                raise SkillctlError(f"number out of range: {n}")
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
        report.problem(f"{name}: {l} is taken, did not link it to {t}")
        return
    CLAUDE_DIR.mkdir(parents=True, exist_ok=True)
    l.symlink_to(t)


def claude_slot_taken(name, report):
    """新装之前检查 L：被别的东西占着就两处都不装，免得两个工具里同名却是不同的 skill。"""
    t, l = AGENTS_DIR / name, CLAUDE_DIR / name
    if (l.exists() or l.is_symlink()) and not points_to(l, t):
        report.problem(f"{name}: {l} is taken by a skill skillctl does not manage, name conflict; "
                       f"installed in neither place")
        return True
    return False


def install_entry(sid, entry, report):
    """让一个 present 条目在本机就位。返回是否做了改动。"""
    repo, path = split_id(sid)
    name = entry["name"]
    t = AGENTS_DIR / name
    try:
        rdir = ensure_repo(repo)
    except SkillctlError as e:
        report.problem(f"{name}: {e}")
        return False
    src = rdir if path == "." else rdir / path
    if not (src / "SKILL.md").is_file():
        report.problem(f"{name}: {path}/SKILL.md is gone at the repo copy's current commit, keeping the installed version")
        return False
    changed = False

    if entry.get("link"):
        if t.is_symlink():
            if not points_to(t, rdir):
                report.problem(f"{name}: {t} points elsewhere, name conflict")
                return False
        elif t.exists():
            report.problem(f"{name}: {t} exists and was not installed by skillctl, name conflict")
            return False
        else:
            if claude_slot_taken(name, report):
                return False
            AGENTS_DIR.mkdir(parents=True, exist_ok=True)
            t.symlink_to(rdir)
            report.info(f"Linked {name} -> {rdir}")
            changed = True
    else:
        commit = head(rdir)
        if t.is_symlink() or (t.exists() and not t.is_dir()):
            report.problem(f"{name}: {t} is taken, name conflict")
            return False
        if not t.exists():
            if claude_slot_taken(name, report):
                return False
            copy_skill(src, sid, name, commit)
            report.info(f"Installed {name} ({sid})")
            changed = True
        else:
            mk = read_marker(t)
            if not mk or mk.get("id") != sid:
                report.problem(f"{name}: {t} was not installed by this entry, name conflict")
                return False
            if content_hash(t) != mk.get("hash"):
                report.problem(f"{name}: modified locally, not overwritten")
            elif mk.get("commit") != commit:
                copy_skill(src, sid, name, commit)
                report.info(f"Reinstalled {name} at {commit[:7]}")
                changed = True
    ensure_claude_link(name, report)
    return changed


def uninstall_dir(t, sid, name, report, reason):
    """删除 skillctl 安装的目录 t 及指向它的软链接；手改过的保留。"""
    if t.is_symlink():
        t.unlink()
        remove_link_to(CLAUDE_DIR / t.name, t)
        report.info(f"{reason} {name}")
        return
    mk = read_marker(t)
    if not mk or mk.get("id") != sid:
        return
    if content_hash(t) != mk.get("hash"):
        report.problem(f"{t.name}: modified locally, not removed")
        return
    shutil.rmtree(t)
    remove_link_to(CLAUDE_DIR / t.name, t)
    report.info(f"{reason} {t.name}")


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
            report.problem(f"{sid} and {items[0][1]} are both named {name} in the manifest, skipping the later {sid}; rename it with add --as")
    return winners


def reconcile(manifest, report):
    """让本机安装状态与清单一致。"""
    skills = manifest["skills"]
    # 1. removed 条目和改名后留下的旧目录
    for p, sid in managed_dirs().items():
        e = skills.get(sid)
        if e is None:
            report.problem(f"{p.name}: no entry for {sid} in the manifest, reported only, not removed")
        elif e.get("state") == "removed":
            uninstall_dir(p, sid, p.name, report, "Uninstalled")
        elif e.get("name") != p.name:
            uninstall_dir(p, sid, p.name, report, "Removed the pre-rename directory")
    # 2. 仓库副本切到清单记录的提交，再装 present 条目
    winners = name_winners(manifest, report)
    repos = sorted({split_id(sid)[0] for sid in winners})
    failed = set()
    missing = [r for r in repos if not (repo_dir(r) / ".git").exists()]
    for repo, (_, err) in run_parallel(ensure_repo, missing).items():
        if err:
            report.problem(f"{repo}: {err}")
            failed.add(repo)
    before = dump_manifest(manifest)
    ready = {repo for repo in repos if repo not in failed and prepare_repo(manifest, repo, report)}
    if dump_manifest(manifest) != before:
        save_manifest(manifest)
    for sid, e in sorted(winners.items()):
        if split_id(sid)[0] in ready:
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
    say("Note: README is out of sync with the manifest; update it on the main Mac (purpose and category are written by hand):")
    for line in drift or proc.stdout.strip().splitlines():
        say(f"  {line}")


def ensure_bin_link():
    target = SCRIPT
    if BIN_LINK.is_symlink() or BIN_LINK.exists():
        if not points_to(BIN_LINK, target):
            warn(f"Note: {BIN_LINK} is taken, did not point it to {target}")
        return
    BIN_LINK.parent.mkdir(parents=True, exist_ok=True)
    BIN_LINK.symlink_to(target)
    say(f"Created command link {BIN_LINK} -> {target}")
    if str(BIN_LINK.parent) not in os.environ.get("PATH", "").split(os.pathsep):
        warn(f"Note: {BIN_LINK.parent} is not on PATH; add it to run skillctl by name")


def cmd_sync(args=None):
    pull_work()
    manifest = load_manifest()
    report = Report()
    reconcile(manifest, report)
    print_unmanaged()
    if report.problems:
        say(f"sync finished with {report.problems} problem(s) to resolve")
    return 1 if report.problems else 0


def print_list(repo, skills, manifest):
    installed = {split_id(sid)[1]: e["name"] for sid, e in present(manifest).items() if split_id(sid)[0] == repo}
    reserved = reserved_names()
    for i, (path, name, desc) in enumerate(skills, start=1):
        if path in installed:
            state = f"installed as {installed[path]}"
        elif name in reserved:
            state = "reserved"
        elif occupied(name) or any(e["name"] == name for e in present(manifest).values()):
            state = "name taken"
        else:
            state = ""
        say(f"{i:>3}. {name or '(no name)'}  [{path}]  {state}")
        if desc:
            say(f"     {desc[:100]}")


def cmd_add(args):
    repo = args.repo
    if not REPO_RE.match(repo):
        raise SkillctlError("repository must be owner/repo")
    if args.as_name and args.prefix:
        raise SkillctlError("--as and --prefix cannot be used together")
    pull_work()
    manifest = load_manifest()
    report = Report()
    reconcile(manifest, report)

    # 已有 skill 在用的仓库沿用清单记录的版本，免得顺带升级它们；新仓库用默认分支最新提交
    pinned = repo in repos_in_use(manifest) and pin_of(manifest, repo)
    fresh = not (repo_dir(repo) / ".git").exists()
    rdir = ensure_repo(repo)
    if pinned:
        checkout(rdir, pinned)
        commit = git(["log", "-1", "--format=%h %cd", "--date=short"], cwd=rdir).stdout.strip()
        say(f"{repo} already has skills in use, installing from the pinned version {commit}; to get the latest upstream, run skillctl update {repo} first")
    elif not fresh:
        try:
            checkout(rdir, fetch_latest(rdir))
        except SkillctlError as e:
            warn(f"Note: {repo}: {e}; using the repo copy as is")
    skills = discover(rdir)
    if not skills:
        raise SkillctlError(f"no SKILL.md found in {repo}")

    interactive = False
    if args.skill:
        wanted = [s.strip() for s in args.skill.split(",") if s.strip()]
        chosen = []
        for w in wanted:
            w = w.rstrip("/") or w
            hit = [s for s in skills if s[0] == w] or [s for s in skills if s[1] == w]
            if not hit:
                raise SkillctlError(f"{repo} has no {w}; available: " + ", ".join(s[1] or s[0] for s in skills))
            if len(hit) > 1:
                raise SkillctlError(f"{repo} has several skills named {w}; use a path instead: " + ", ".join(s[0] for s in hit))
            if hit[0] not in chosen:
                chosen.append(hit[0])
    else:
        print_list(repo, skills, manifest)
        if not is_tty():
            say("stdin is not a terminal, nothing installed. Choose skills with --skill")
            return 2
        if args.link:
            raise SkillctlError("--link requires --skill")
        interactive = True
        if len(skills) == 1:
            chosen = skills
        else:
            text = ask("Numbers to install (e.g. 1,3,5-7), Enter to cancel: ")
            if not text:
                say("Cancelled")
                return 0
            chosen = [skills[n - 1] for n in parse_selection(text, len(skills))]
    if args.as_name and len(chosen) != 1:
        raise SkillctlError("--as takes a single skill")
    if args.link and len(chosen) != 1:
        raise SkillctlError("--link takes a single skill")

    existing = {split_id(sid)[1]: sid for sid in present(manifest) if split_id(sid)[0] == repo}
    prefix = args.prefix
    new_items = [c for c in chosen if c[0] not in existing]
    if interactive and not prefix and len(new_items) > 1:
        prefix = ask("Common prefix (e.g. gstack-), Enter for none: ")

    plan, taken, refused = [], [], 0
    for path, upstream, _ in chosen:
        sid = f"{repo}:{path}"
        if path in existing and not args.as_name:
            say(f"{upstream or path} is already installed as {manifest['skills'][sid]['name']}, skipping")
            continue
        if args.as_name:
            name = args.as_name
        elif not upstream:
            raise SkillctlError(f"{path}/SKILL.md has no name; set the install name with --as")
        else:
            name = apply_prefix(prefix, upstream)
        problem = name_problem(name, manifest, sid, taken)
        while problem and interactive:
            alias = ask(f"{name} {problem}. Alias, or Enter to skip: ")
            if not alias:
                break
            name = alias
            problem = name_problem(name, manifest, sid, taken)
        if problem:
            report.problem(f"{name}: {problem}, not installed")
            refused += 1
            continue
        taken.append(name)
        plan.append((sid, name))

    if not plan:
        return 1 if refused else 0
    if interactive:
        for sid, name in plan:
            say(f"  {name}  ←  {sid}")
        if ask("Install? [y/N] ").lower() not in ("y", "yes"):
            say("Cancelled")
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
    if not pinned:
        set_pin(manifest, repo, head(rdir), stamp)
    save_manifest(manifest)
    reconcile(manifest, report)
    remind_readme()
    return 1 if (refused or report.problems) else 0


def cmd_remove(args):
    pull_work()
    manifest = load_manifest()
    hits = [sid for sid, e in present(manifest).items() if e["name"] == args.name]
    if not hits:
        raise SkillctlError(f"no skill named {args.name} in the manifest; skills not managed by skillctl are left alone")
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
        raise SkillctlError(f"file not found: {src}")
    other = parse_manifest(src.read_text(encoding="utf-8"), src)
    manifest = load_manifest()
    merged, changed = merge_manifests(manifest, other)
    if not changed:
        say("Nothing to merge")
    else:
        say(f"The merge brings {len(changed)} change(s):")
        for sid in sorted(changed):
            say("  " + describe_change(sid, manifest["skills"].get(sid), merged["skills"][sid]))
        if not args.yes:
            if not is_tty():
                say("stdin is not a terminal, nothing merged. Review the changes, then re-run with --yes")
                return 2
            if ask("Merge, then install and uninstall to match? [y/N] ").lower() not in ("y", "yes"):
                say("Cancelled, the manifest and installed skills are unchanged")
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
            raise SkillctlError(f"no skills from {args.repo} in the manifest")
        by_repo = {args.repo: by_repo[args.repo]}

    upgraded = 0
    local = [repo for repo in sorted(by_repo) if (repo_dir(repo) / ".git").exists()]
    latest = run_parallel(lambda repo: fetch_latest(repo_dir(repo)), local)
    for repo in local:
        rdir = repo_dir(repo)
        new, err = latest[repo]
        if err:
            report.problem(f"{repo}: {err}")
            continue
        old = head(rdir)
        if old == new:
            continue
        say(f"{repo}: {old[:7]} -> {new[:7]}")
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
            say(f"  {e['name']}: {len(files)} file(s) changed" + (", the skill was deleted upstream" if gone else ""))
            for f in files[:10]:
                say(f"    {f}")
            if len(files) > 10:
                say(f"    ... and {len(files) - 10} more")
        try:
            checkout(rdir, new)
        except SkillctlError as e:
            report.problem(f"{repo}: {e}")
            continue
        set_pin(manifest, repo, new)
        save_manifest(manifest)
        upgraded += 1
        for sid, e in by_repo[repo]:
            t = AGENTS_DIR / e["name"]
            mk = read_marker(t)
            if sid in changed_ids or e.get("link") or not mk or mk.get("id") != sid:
                install_entry(sid, e, report)
            elif content_hash(t) == mk.get("hash"):
                write_marker(t, sid, new)
    if upgraded:
        say(f"Pinned new versions of {upgraded} repo(s) in the manifest; commit and push it, and the other Mac installs the same versions on sync")
    return 1 if report.problems else 0


def cmd_list(args):
    manifest = load_manifest()
    rows = []
    for sid, e in sorted(present(manifest).items(), key=lambda x: x[1]["name"]):
        t = AGENTS_DIR / e["name"]
        if e.get("link"):
            state = "linked" if t.is_symlink() else "missing"
            commit = ""
            rdir = repo_dir(split_id(sid)[0])
            if (rdir / ".git").exists():
                commit = head(rdir)[:7]
        else:
            mk = read_marker(t)
            if not mk or mk.get("id") != sid:
                state, commit = ("missing" if not t.exists() else "conflict"), ""
            else:
                commit = mk.get("commit", "")[:7]
                state = "ok" if content_hash(t) == mk.get("hash") else "modified"
        rows.append((e["name"], sid, commit, state))
    width = max((len(r[0]) for r in rows), default=4)
    for name, sid, commit, state in rows:
        say(f"{name:<{width}}  {commit:<7}  {state:<8}  {sid}")
    say(f"{len(rows)} managed")
    print_unmanaged()
    return 0


def print_unmanaged():
    extra = unmanaged_skills()
    if not extra:
        return
    say()
    say(f"Unmanaged skills ({len(extra)}, not in the manifest, skillctl leaves them alone):")
    width = max(len(n) for n in extra)
    for name, (where, detail, hint) in sorted(extra.items()):
        say(f"{name:<{width}}  {where}  {detail}".rstrip())
        if hint:
            say(f"{'':<{width}}  to manage it: move the directory to a backup, then run {hint}")


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
        where = ", ".join(label for label, _ in items)
        detail, hint = "", None
        for _, p in items:
            src = openskills_source(p)
            if src:
                detail = f"source {src[0]}:{src[1]}"
                hint = f"skillctl add {src[0]} --skill {src[1]}"
                break
        if not detail:
            links = sorted({os.readlink(str(p)) for _, p in items if p.is_symlink()})
            detail = f"symlink to {', '.join(links)}" if links else "source unknown"
        out[name] = (where, detail, hint)
    return out


def check_issues():
    issues = []
    # 工作 clone
    if git_dir() is not None:
        if pending_path().exists():
            issues.append("the work clone has a pending manifest from an interrupted run; run skillctl sync to merge it")
        if git(["fetch", "--quiet"], cwd=WORK, check=False).returncode != 0:
            issues.append("failed to fetch the work clone, cannot tell whether it is behind")
        up = upstream_ref()
        if up:
            counts = git(["rev-list", "--left-right", "--count", f"HEAD...{up}"], cwd=WORK).stdout.split()
            ahead, behind = int(counts[0]), int(counts[1])
            if behind:
                issues.append(f"the work clone is {behind} commit(s) behind; run skillctl sync")
            if ahead:
                issues.append(f"the work clone has {ahead} unpushed commit(s)")
        if git(["status", "--porcelain", "--", "skills.json"], cwd=WORK).stdout.strip():
            issues.append("skills.json has uncommitted changes (main Mac: not committed and pushed yet; second Mac: changes not yet merged on the main Mac)")

    # 清单与安装状态
    manifest = load_manifest()
    names = {}
    for sid, e in present(manifest).items():
        names.setdefault(e["name"], []).append(sid)
    for name, sids in names.items():
        if len(sids) > 1:
            issues.append(f"{', '.join(sids)} are all named {name} in the manifest")
    for sid, e in present(manifest).items():
        name = e["name"]
        t, l = AGENTS_DIR / name, CLAUDE_DIR / name
        rdir = repo_dir(split_id(sid)[0])
        if e.get("link"):
            if not points_to(t, rdir):
                issues.append(f"{name}: not link-installed as the manifest says; run skillctl sync")
        else:
            mk = read_marker(t)
            if not t.exists():
                issues.append(f"{name}: not installed; run skillctl sync")
            elif not mk or mk.get("id") != sid:
                issues.append(f"{name}: {t} was not installed by this entry, name conflict")
            elif content_hash(t) != mk.get("hash"):
                issues.append(f"{name}: modified locally")
            elif mk.get("commit") != pin_of(manifest, split_id(sid)[0]):
                issues.append(f"{name}: installed version differs from the pinned version; run skillctl sync")
        if t.exists() and not points_to(l, t):
            issues.append(f"{name}: {l} does not point to {t}")
    for p, sid in managed_dirs().items():
        e = manifest["skills"].get(sid)
        if e is None:
            issues.append(f"{p.name}: no entry for {sid} in the manifest")
        elif e.get("state") == "removed" or e.get("name") != p.name:
            issues.append(f"{p.name}: removed or renamed in the manifest; run skillctl sync")

    # 名字冲突、失效软链接、目录名与 name 不一致
    groups = {}
    for d in scan_dirs():
        if not d.is_dir():
            continue
        for p in sorted(d.iterdir()):
            if p.name.startswith("."):
                continue
            if p.is_symlink() and not p.exists():
                issues.append(f"broken symlink: {p}")
                continue
            if not (p / "SKILL.md").is_file():
                continue
            groups.setdefault(p.name, []).append(p)
            fm_name, _ = read_frontmatter(p / "SKILL.md")
            if fm_name and fm_name != p.name:
                issues.append(f"{p}: directory name differs from name ({fm_name})")
    for name, paths in sorted(groups.items()):
        distinct = {}
        for p in paths:
            real = os.path.realpath(str(p))
            if real not in distinct:
                distinct[real] = content_hash(Path(real))
        if len(set(distinct.values())) > 1:
            issues.append(f"name conflict {name}: " + ", ".join(str(p) for p in paths))

    # 仓库版本与上游更新；查询上游并发进行
    repos = sorted(repos_in_use(manifest))
    remotes = run_parallel(
        lambda repo: git(["ls-remote", f"{GIT_BASE}{repo}", "HEAD"], check=False, timeout=LS_REMOTE_TIMEOUT),
        [repo for repo in repos if pin_of(manifest, repo)])
    for repo in repos:
        pin, rdir = pin_of(manifest, repo), repo_dir(repo)
        if not pin:
            issues.append(f"{repo}: no pinned version in the manifest; run skillctl sync")
            continue
        if (rdir / ".git").exists() and head(rdir) != pin:
            issues.append(f"{repo}: repo copy is not at the pinned version; run skillctl sync")
        remote = remotes[repo][0]
        if remote.returncode != 0 or not remote.stdout.strip():
            issues.append(f"{repo}: failed to query upstream, cannot tell whether it has updates")
        elif remote.stdout.split()[0] != pin:
            issues.append(f"{repo}: upstream has updates; run skillctl update {repo} to upgrade")
    return issues


def cmd_check(args):
    issues = check_issues()
    for i in issues:
        say(f"  ! {i}")
    say(f"{len(issues)} problem(s) found" if issues else "All checks passed")
    return 1 if issues else 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="skillctl", description="Manage skills across agents and machines")
    sub = parser.add_subparsers(dest="command")
    p = sub.add_parser("add", help="pick and install skills from a GitHub repository")
    p.add_argument("repo", help="owner/repo")
    p.add_argument("--skill", help="skills to install, by name or path in the repository, comma separated")
    p.add_argument("--as", dest="as_name", help="install name for a single skill; on an installed skill, renames it")
    p.add_argument("--prefix", help="prefix for the skills newly installed in this run")
    p.add_argument("--link", action="store_true", help="symlink the repo copy root as the skill directory")
    p = sub.add_parser("remove", help="uninstall a skill and mark it removed in the manifest")
    p.add_argument("name", help="install name")
    sub.add_parser("sync", help="pull the work clone, merge the manifest, and make installs match it")
    p = sub.add_parser("merge", help="merge another machine's manifest")
    p.add_argument("file")
    p.add_argument("-y", "--yes", action="store_true", help="merge without asking")
    p = sub.add_parser("update", help="fetch the latest upstream, reinstall changed skills, and pin the new versions")
    p.add_argument("repo", nargs="?")
    sub.add_parser("list", help="list managed and unmanaged skills")
    sub.add_parser("check", help="read-only health check")
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
        warn(f"Error: {e}")
        return 1
    except KeyboardInterrupt:
        warn("Interrupted")
        return 130


if __name__ == "__main__":
    sys.exit(main())
