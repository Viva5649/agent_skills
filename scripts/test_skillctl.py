#!/usr/bin/env python3
"""skillctl 行为测试。用本地临时 git 仓库模拟 GitHub，不联网。

运行：python3 scripts/test_skillctl.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "skillctl.py"
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
import skillctl as sk  # noqa: E402

GIT_ENV = dict(
    os.environ,
    GIT_AUTHOR_NAME="test", GIT_AUTHOR_EMAIL="test@example.com",
    GIT_COMMITTER_NAME="test", GIT_COMMITTER_EMAIL="test@example.com",
    GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0",
)


def git(args, cwd):
    return subprocess.run(["git"] + args, cwd=str(cwd), env=GIT_ENV, check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           universal_newlines=True).stdout


def skill_md(name, body="v1"):
    return f"---\nname: {name}\ndescription: {name} 的描述\n---\n\n# {name}\n\n{body}\n"


class Env:
    """一个临时世界：上游仓库、agent_skills 裸仓库、若干台机器。"""

    def __init__(self):
        self.root = Path(tempfile.mkdtemp(prefix="skillctl-test-"))
        self.remotes = self.root / "remotes"
        self.remotes.mkdir()
        seed = self.root / "seed"
        (seed / "scripts").mkdir(parents=True)
        shutil.copy(str(SRC), str(seed / "scripts" / "skillctl.py"))
        (seed / "README.md").write_text("seed\n")
        git(["init", "-q", "-b", "main"], seed)
        git(["add", "."], seed)
        git(["commit", "-q", "-m", "seed"], seed)
        self.bare = self.remotes / "me" / "agent_skills"
        self.bare.parent.mkdir(parents=True)
        git(["clone", "-q", "--bare", str(seed), str(self.bare)], self.root)

    def upstream(self, repo, files, message="update", delete=()):
        d = self.remotes / repo
        if not d.exists():
            d.mkdir(parents=True)
            git(["init", "-q", "-b", "main"], d)
        for rel, text in files.items():
            p = d / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
        for rel in delete:
            shutil.rmtree(str(d / rel))
        git(["add", "-A"], d)
        git(["commit", "-q", "-m", message], d)
        return d

    def machine(self, name):
        m = Machine(self, name)
        return m

    def cleanup(self):
        shutil.rmtree(str(self.root), ignore_errors=True)


class Machine:
    def __init__(self, env, name):
        self.env = env
        self.home = env.root / name / "home"
        self.home.mkdir(parents=True)
        self.work = env.root / name / "agent_skills"
        git(["clone", "-q", str(env.bare), str(self.work)], env.root)
        self.agents = self.home / ".agents" / "skills"
        self.claude = self.home / ".claude" / "skills"

    def run(self, *args, stdin=None, tty=False):
        env = dict(GIT_ENV, HOME=str(self.home), SKILLCTL_GIT_BASE=str(self.env.remotes) + "/")
        env.pop("SKILLCTL_FORCE_TTY", None)
        if tty:
            env["SKILLCTL_FORCE_TTY"] = "1"
        proc = subprocess.run([sys.executable, str(self.work / "scripts" / "skillctl.py")] + list(args),
                              cwd=str(self.home), env=env, input=stdin if stdin is not None else "",
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        return proc.returncode, proc.stdout

    def manifest(self):
        p = self.work / "skills.json"
        return json.loads(p.read_text()) if p.exists() else {"skills": {}}

    def publish(self, message="skills"):
        git(["add", "skills.json"], self.work)
        git(["commit", "-q", "-m", message], self.work)
        git(["push", "-q"], self.work)

    def skill_name(self, name):
        return sk.read_frontmatter(self.agents / name / "SKILL.md")[0]


class Base(unittest.TestCase):
    def setUp(self):
        self.env = Env()
        self.env.upstream("acme/tools", {
            "skills/alpha/SKILL.md": skill_md("alpha"),
            "skills/alpha/ref.md": "ref\n",
            "skills/beta/SKILL.md": skill_md("beta"),
            "skills/beta/node_modules/pkg/index.js": "x\n",
        })
        self.m = self.env.machine("main")

    def tearDown(self):
        self.env.cleanup()

    def ok(self, machine, *args, **kw):
        rc, out = machine.run(*args, **kw)
        self.assertEqual(rc, 0, out)
        return out

    def check_clean(self, machine):
        """check 只允许报"清单有未提交修改"这一项。"""
        rc, out = machine.run("check")
        issues = [l for l in out.splitlines() if l.strip().startswith("!")]
        self.assertTrue(all("skills.json 有未提交的修改" in l for l in issues), out)


# 1. 清单合并

class MergeTest(unittest.TestCase):
    def test_last_writer_wins_and_tombstones(self):
        local = {"version": 1, "skills": {
            "a/b:x": {"name": "x", "state": "present", "updated_at": "2026-01-01T00:00:00Z"},
            "a/b:y": {"name": "y", "state": "present", "updated_at": "2026-01-03T00:00:00Z"},
            "a/b:t": {"name": "t", "state": "present", "updated_at": "2026-01-05T00:00:00Z"},
        }}
        other = {"version": 1, "skills": {
            "a/b:x": {"name": "x", "state": "removed", "updated_at": "2026-01-02T00:00:00Z"},
            "a/b:y": {"name": "y", "state": "removed", "updated_at": "2026-01-02T00:00:00Z"},
            "a/b:z": {"name": "z", "state": "present", "updated_at": "2026-01-01T00:00:00Z"},
            "a/b:t": {"name": "t2", "state": "present", "updated_at": "2026-01-05T00:00:00Z"},
        }}
        merged, changed = sk.merge_manifests(local, other)
        s = merged["skills"]
        self.assertEqual(s["a/b:x"]["state"], "removed")   # 较晚的删除覆盖较早的新增
        self.assertEqual(s["a/b:y"]["state"], "present")   # 较晚的新增不被较早的删除覆盖
        self.assertEqual(s["a/b:z"]["name"], "z")          # 只有一边有的保留
        self.assertEqual(s["a/b:t"]["name"], "t")          # 时间相同保留本机
        self.assertEqual(sorted(changed), ["a/b:x", "a/b:z"])

    def test_timezone_aware_comparison(self):
        self.assertTrue(sk.now().endswith("+08:00"))
        # 同一时刻：07:30Z 等于 15:30+08:00；15:00+08:00 比 07:30Z 早
        older = {"version": 1, "skills": {"a/b:x": {"name": "x", "state": "removed",
                                                    "updated_at": "2026-01-01T15:00:00+08:00"}}}
        newer = {"version": 1, "skills": {"a/b:x": {"name": "x", "state": "present",
                                                    "updated_at": "2026-01-01T07:30:00Z"}}}
        self.assertEqual(sk.merge_manifests(older, newer)[0]["skills"]["a/b:x"]["state"], "present")
        self.assertEqual(sk.merge_manifests(newer, older)[0]["skills"]["a/b:x"]["state"], "present")

    def test_same_content_dumps_identically(self):
        a = {"version": 1, "skills": {"a/b:x": {"name": "x", "state": "present",
                                                "updated_at": "2026-01-01T08:00:00+08:00"}}}
        b = {"version": 1, "skills": {"a/b:y": {"name": "y", "state": "present",
                                                "updated_at": "2026-01-02T08:00:00+08:00"}}}
        self.assertEqual(sk.dump_manifest(sk.merge_manifests(a, b)[0]),
                         sk.dump_manifest(sk.merge_manifests(b, a)[0]))


# 2. 安装

class InstallTest(Base):
    def test_install_rename_and_idempotent(self):
        out = self.ok(self.m, "add", "acme/tools", "--skill", "alpha")
        t, l = self.m.agents / "alpha", self.m.claude / "alpha"
        self.assertTrue(t.is_dir() and not t.is_symlink())
        self.assertTrue((t / ".skillctl.json").is_file())
        self.assertTrue((t / "ref.md").is_file())
        self.assertEqual(os.readlink(str(l)), str(t))
        link = self.m.home / ".local" / "bin" / "skillctl"
        self.assertEqual(os.readlink(str(link)), str((self.m.work / "scripts" / "skillctl.py").resolve()))
        self.assertIn("已创建命令链接", out)

        before = (t / ".skillctl.json").stat().st_mtime_ns
        out = self.ok(self.m, "sync")
        self.assertNotIn("已安装", out)
        self.assertNotIn("已重装", out)
        self.assertEqual((t / ".skillctl.json").stat().st_mtime_ns, before)

        self.ok(self.m, "add", "acme/tools", "--skill", "alpha", "--as", "acme-alpha")
        self.assertFalse(t.exists() or l.is_symlink())
        self.assertEqual(self.m.skill_name("acme-alpha"), "acme-alpha")
        self.assertEqual(self.m.manifest()["skills"]["acme/tools:skills/alpha"]["name"], "acme-alpha")
        self.check_clean(self.m)

    def test_list_shows_unmanaged(self):
        self.ok(self.m, "add", "acme/tools", "--skill", "alpha")
        old = self.m.claude / "legacy"
        old.mkdir(parents=True)
        (old / "SKILL.md").write_text(skill_md("legacy"))
        (old / ".openskills.json").write_text(json.dumps(
            {"repoUrl": "https://github.com/acme/tools", "subpath": "skills/legacy"}))
        stray = self.m.agents / "stray"
        stray.mkdir(parents=True)
        (stray / "SKILL.md").write_text(skill_md("stray"))
        out = self.ok(self.m, "list")
        unmanaged = out.split("未托管的 skill", 1)[1]
        self.assertIn("skillctl add acme/tools --skill skills/legacy", unmanaged)
        self.assertIn("stray", unmanaged)
        self.assertIn("来源未知", unmanaged)
        self.assertNotIn("alpha", unmanaged)

    def test_bin_link_not_overwritten(self):
        link = self.m.home / ".local" / "bin" / "skillctl"
        link.parent.mkdir(parents=True)
        link.write_text("mine")
        rc, out = self.m.run("list")
        self.assertEqual(link.read_text(), "mine")
        self.assertIn("已被占用", out)


# 3. 手改保护

class ProtectTest(Base):
    def test_local_edit_survives_sync_update_remove(self):
        self.ok(self.m, "add", "acme/tools", "--skill", "alpha")
        f = self.m.agents / "alpha" / "ref.md"
        f.write_text("my edit\n")
        rc, out = self.m.run("sync")
        self.assertIn("本地手改", out)
        self.env.upstream("acme/tools", {"skills/alpha/ref.md": "upstream v2\n"})
        self.m.run("update")
        self.assertEqual(f.read_text(), "my edit\n")
        rc, out = self.m.run("remove", "alpha")
        self.assertTrue(f.exists())
        self.assertIn("没有删除", out)
        self.assertEqual(self.m.manifest()["skills"]["acme/tools:skills/alpha"]["state"], "removed")


# 4. 冲突拒绝

class ConflictTest(Base):
    def test_unmanaged_dir_blocks_install(self):
        d = self.m.agents / "alpha"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(skill_md("alpha", "mine"))
        rc, out = self.m.run("add", "acme/tools", "--skill", "alpha")
        self.assertEqual(rc, 1)
        self.assertIn("mine", (d / "SKILL.md").read_text())
        self.ok(self.m, "add", "acme/tools", "--skill", "alpha", "--as", "acme-alpha")

    def test_reserved_names(self):
        self.env.upstream("acme/tools", {"skills/review/SKILL.md": skill_md("review"),
                                         "skills/imagegen/SKILL.md": skill_md("imagegen")})
        sysdir = self.m.home / ".codex" / "skills" / ".system" / "imagegen"
        sysdir.mkdir(parents=True)
        (sysdir / "SKILL.md").write_text(skill_md("imagegen"))
        for name in ("review", "imagegen"):
            rc, out = self.m.run("add", "acme/tools", "--skill", name)
            self.assertEqual(rc, 1, out)
            self.assertIn("保留名", out)
            self.assertFalse((self.m.agents / name).exists())


# 5. 更新

class UpdateTest(Base):
    def test_only_changed_reinstalled_and_deleted_kept(self):
        self.ok(self.m, "add", "acme/tools", "--skill", "alpha,beta")
        self.assertFalse((self.m.agents / "beta" / "node_modules").exists())
        (self.m.agents / "beta" / "node_modules").mkdir()   # 本机装依赖不算手改
        beta_ino = (self.m.agents / "beta" / "SKILL.md").stat().st_ino
        self.env.upstream("acme/tools", {"skills/alpha/ref.md": "v2\n"})
        out = self.ok(self.m, "update")
        self.assertIn("alpha：1 个文件有变化", out)
        self.assertNotIn("beta：", out)
        self.assertEqual((self.m.agents / "alpha" / "ref.md").read_text(), "v2\n")
        self.assertEqual((self.m.agents / "beta" / "SKILL.md").stat().st_ino, beta_ino)
        self.check_clean(self.m)

        self.env.upstream("acme/tools", {}, delete=["skills/beta"])
        rc, out = self.m.run("update")
        self.assertIn("上游已删除", out)
        self.assertTrue((self.m.agents / "beta" / "SKILL.md").exists())


# 6. 交互勾选和前缀

class InteractiveTest(Base):
    def setUp(self):
        super().setUp()
        self.env.upstream("acme/suite", {
            "office/SKILL.md": skill_md("office"),
            "review/SKILL.md": skill_md("review"),
            "gx-ready/SKILL.md": skill_md("gx-ready"),
        })

    def test_parse_and_prefix_helpers(self):
        self.assertEqual(sk.parse_selection("1, 3-4，2", 5), [1, 3, 4, 2])
        with self.assertRaises(sk.SkillctlError):
            sk.parse_selection("9", 3)
        self.assertEqual(sk.apply_prefix("gx", "office"), "gx-office")
        self.assertEqual(sk.apply_prefix("gx-", "gx-ready"), "gx-ready")

    def test_non_tty_lists_only(self):
        rc, out = self.m.run("add", "acme/suite")
        self.assertEqual(rc, 2, out)
        self.assertIn("office", out)
        self.assertFalse(self.m.agents.exists() and any(self.m.agents.iterdir()))

    def test_tty_selection_prefix_alias(self):
        taken = self.m.agents / "gx-office"
        taken.mkdir(parents=True)
        (taken / "SKILL.md").write_text(skill_md("gx-office"))
        # 列表按路径排序：gx-ready、office、review
        out = self.ok(self.m, "add", "acme/suite", tty=True, stdin="1-3\ngx\ngx-office2\ny\n")
        names = {e["name"] for e in self.m.manifest()["skills"].values()}
        self.assertEqual(names, {"gx-ready", "gx-office2", "gx-review"})
        self.assertEqual(self.m.skill_name("gx-review"), "gx-review")

        out = self.ok(self.m, "add", "acme/suite", "--skill", "review", "--prefix", "zz")
        self.assertIn("已装为 gx-review", out)
        self.assertEqual(self.m.manifest()["skills"]["acme/suite:review"]["name"], "gx-review")


# 7. 两台流转

class TwoMachineTest(Base):
    def test_roundtrip(self):
        self.env.upstream("acme/tools", {"skills/gamma/SKILL.md": skill_md("gamma"),
                                         "skills/delta/SKILL.md": skill_md("delta")})
        second = self.env.machine("second")

        self.ok(self.m, "add", "acme/tools", "--skill", "alpha")
        self.m.publish("add alpha")
        self.ok(second, "sync")
        self.assertTrue((second.agents / "alpha").is_dir())

        self.ok(second, "add", "acme/tools", "--skill", "beta")
        self.assertIn("skills.json", git(["status", "--porcelain"], second.work))
        theirs = str(second.work / "skills.json")
        before = (self.m.work / "skills.json").read_text()
        rc, out = self.m.run("merge", theirs)                      # 非终端且没加 --yes：只列出
        self.assertEqual(rc, 2, out)
        self.assertIn("新增 beta", out)
        out = self.ok(self.m, "merge", theirs, tty=True, stdin="n\n")  # 终端里拒绝：不改动
        self.assertIn("已取消", out)
        self.assertEqual((self.m.work / "skills.json").read_text(), before)
        self.assertFalse((self.m.agents / "beta").exists())
        self.ok(self.m, "merge", theirs, tty=True, stdin="y\n")
        self.assertTrue((self.m.agents / "beta").is_dir())
        self.m.publish("merge beta")
        self.ok(second, "sync")
        self.assertEqual(git(["diff", "--", "skills.json"], second.work), "")

        # 副机带着未提交修改，主力机又推送了新改动
        self.ok(second, "add", "acme/tools", "--skill", "gamma")
        self.ok(self.m, "add", "acme/tools", "--skill", "delta")
        self.m.publish("add delta")
        self.ok(second, "sync")
        self.assertEqual(git(["rev-parse", "HEAD"], second.work), git(["rev-parse", "origin/main"], second.work))
        names = {e["name"] for e in second.manifest()["skills"].values()}
        self.assertEqual(names, {"alpha", "beta", "gamma", "delta"})
        added = [l for l in git(["diff", "--", "skills.json"], second.work).splitlines()
                 if l.startswith("+") and not l.startswith("+++")]
        self.assertTrue(any("gamma" in l for l in added))
        self.assertFalse(any("delta" in l for l in added))
        self.assertTrue((second.agents / "delta").is_dir())

        # 中断遗留的临时文件
        pending = second.work / ".git" / "skillctl-pending.json"
        data = second.manifest()
        data["skills"]["acme/tools:skills/beta"] = {"name": "beta", "state": "removed",
                                                    "updated_at": "2099-01-01T08:00:00+08:00"}
        pending.write_text(json.dumps(data))
        self.ok(second, "sync")
        self.assertFalse(pending.exists())
        self.assertEqual(second.manifest()["skills"]["acme/tools:skills/beta"]["state"], "removed")
        self.assertFalse((second.agents / "beta").exists())


class LinkTest(Base):
    def test_link_install(self):
        self.env.upstream("acme/kit", {"SKILL.md": skill_md("kit"),
                                       "office/SKILL.md": skill_md("office"),
                                       "bin/tool": "x\n"})
        self.ok(self.m, "add", "acme/kit", "--skill", ".", "--link")
        self.ok(self.m, "add", "acme/kit", "--skill", "office", "--prefix", "kit-")
        t = self.m.agents / "kit"
        self.assertTrue(t.is_symlink())
        self.assertTrue((self.m.claude / "kit" / "bin" / "tool").is_file())
        self.assertEqual(self.m.skill_name("kit-office"), "kit-office")
        self.check_clean(self.m)
        self.ok(self.m, "remove", "kit")
        self.assertFalse(t.is_symlink() or (self.m.claude / "kit").is_symlink())
        self.assertTrue((self.m.home / ".local/share/agent-skills/repos/acme/kit/SKILL.md").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
