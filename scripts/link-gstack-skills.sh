#!/usr/bin/env bash
# 把 external/gstack 里选定的 skill 以 gstack- 前缀链接到 ~/.claude/skills/
#
# 只装 WANTED 里列的 skill，不像 gstack 官方 ./setup 那样一次装 59 个。
# 链接逻辑对齐 setup 的 _link_skill_runtime_assets：SKILL.md 之外的同级资源
# 全部链过去，所以上游给某个 skill 新增 references/ templates/ 等目录时，
# 重跑本脚本即可自动跟上，不需要改脚本。
#
# 用法：
#   ./scripts/link-gstack-skills.sh          # 按 WANTED 安装/刷新
#   ./scripts/link-gstack-skills.sh --prune  # 额外删掉 WANTED 之外的 gstack-* 残留
#
# 升级 gstack 后重跑：
#   git submodule update --remote -- external/gstack && ./scripts/link-gstack-skills.sh

set -euo pipefail

# ─── 想要的 skill，按需增删 ──────────────────────────────────
WANTED=(
  office-hours
  plan-ceo-review
  plan-eng-review
)

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GSTACK_SRC="$REPO_ROOT/external/gstack"
SKILLS_DIR="$HOME/.claude/skills"
GSTACK_LINK="$SKILLS_DIR/gstack"
PRUNE=0
[ "${1:-}" = "--prune" ] && PRUNE=1

[ -f "$GSTACK_SRC/SKILL.md" ] || {
  echo "错误：$GSTACK_SRC 不像 gstack 仓库，先跑 git submodule update --init" >&2
  exit 1
}
mkdir -p "$SKILLS_DIR"

# ─── 总入口软链 ──────────────────────────────────────────────
# 三个 SKILL.md 内部把 ~/.claude/skills/gstack/bin/... 和 ETHOS.md 写死了，
# 这个软链让那些绝对路径解析得到，磁盘上仍然只有 submodule 一份。
if [ -L "$GSTACK_LINK" ]; then
  cur="$(readlink "$GSTACK_LINK")"
  if [ "$cur" != "$GSTACK_SRC" ]; then
    echo "刷新入口软链：$cur -> $GSTACK_SRC"
    rm -f "$GSTACK_LINK"
    ln -s "$GSTACK_SRC" "$GSTACK_LINK"
  fi
elif [ -e "$GSTACK_LINK" ]; then
  echo "错误：$GSTACK_LINK 已存在且不是软链（可能是独立 clone）。" >&2
  echo "      先移走它，或改用 gstack 官方 ./setup --prefix。" >&2
  exit 1
else
  echo "建立入口软链：$GSTACK_LINK -> $GSTACK_SRC"
  ln -s "$GSTACK_SRC" "$GSTACK_LINK"
fi

# ─── 逐个 skill 建外壳目录 ───────────────────────────────────
# Claude Code 只扫 ~/.claude/skills/<名字>/SKILL.md 这一层，不递归，
# 所以必须是真实目录加内部软链，不能整个目录软链过去。
linked=()
for name in "${WANTED[@]}"; do
  src="$GSTACK_SRC/$name"
  if [ ! -f "$src/SKILL.md" ]; then
    echo "跳过 $name：上游已不存在或改名" >&2
    continue
  fi

  # 目录名以 frontmatter 的 name: 为准，与 setup 一致
  skill_name="$(grep -m1 '^name:' "$src/SKILL.md" | sed 's/^name:[[:space:]]*//' | tr -d '[:space:]')"
  [ -n "$skill_name" ] || skill_name="$name"
  case "$skill_name" in
    gstack-*) link_name="$skill_name" ;;
    *)        link_name="gstack-$skill_name" ;;
  esac

  dst="$SKILLS_DIR/$link_name"
  [ -L "$dst" ] && rm -f "$dst"   # 旧版整目录软链，升级掉
  mkdir -p "$dst"

  rm -rf "$dst/SKILL.md"
  ln -s "$GSTACK_LINK/$name/SKILL.md" "$dst/SKILL.md"

  # SKILL.md 之外的同级资源全链过去，排除项与 setup 保持一致
  for asset in "$src"/*; do
    [ -e "$asset" ] || continue
    a="$(basename "$asset")"
    case "$a" in
      SKILL.md|node_modules|dist|test|*.tmpl) continue ;;
    esac
    rm -rf "${dst:?}/$a"
    ln -s "$GSTACK_LINK/$name/$a" "$dst/$a"
  done

  linked+=("$link_name")
done

echo "已链接：${linked[*]:-（无）}"

# ─── 清理 WANTED 之外的 gstack-* 残留 ────────────────────────
if [ "$PRUNE" -eq 1 ]; then
  for d in "$SKILLS_DIR"/gstack-*; do
    [ -e "$d" ] || continue
    b="$(basename "$d")"
    keep=0
    for l in "${linked[@]:-}"; do [ "$b" = "$l" ] && keep=1; done
    [ "$keep" -eq 1 ] && continue
    echo "清理：$b"
    rm -rf "$d"
  done
fi

# ─── 断链自检 ────────────────────────────────────────────────
broken=0
for l in "${linked[@]:-}"; do
  while IFS= read -r f; do
    echo "断链：$f" >&2
    broken=1
  done < <(find "$SKILLS_DIR/$l" -maxdepth 1 -type l ! -exec test -e {} \; -print 2>/dev/null)
done
[ "$broken" -eq 0 ] && echo "自检通过，无断链。"
