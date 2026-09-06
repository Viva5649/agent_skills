#!/usr/bin/env bash
# 把 third_party/gstack 里选定的 skill 以 gstack- 前缀链接到 skill 目录
#
# 只装 WANTED 里列的 skill，不像 gstack 官方 ./setup 那样一次装 61 个。
# 链接逻辑对齐 setup 的 _link_skill_runtime_assets：SKILL.md 之外的同级资源
# 全部链过去，所以上游给某个 skill 新增 references/ templates/ 等目录时，
# 重跑本脚本即可自动跟上，不需要改脚本。
#
# 目标目录有两个：~/.claude/skills 给 Claude Code，~/.agents/skills 给其他
# agent。后者只在已存在时处理，本机没有这套约定就跳过，不主动创建。
#
# 用法：
#   ./scripts/link-gstack-skills.sh          # 按 WANTED 安装/刷新
#   ./scripts/link-gstack-skills.sh --prune  # 额外删掉 WANTED 之外的 gstack-* 残留
#
# 升级 gstack 后重跑：
#   git submodule update --remote -- third_party/gstack && ./scripts/link-gstack-skills.sh

set -euo pipefail

# ─── 想要的 skill，按需增删 ──────────────────────────────────
WANTED=(
  office-hours
  plan-ceo-review
  plan-eng-review
)

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GSTACK_SRC="$REPO_ROOT/third_party/gstack"
PRUNE=0
[ "${1:-}" = "--prune" ] && PRUNE=1

[ -f "$GSTACK_SRC/SKILL.md" ] || {
  echo "错误：$GSTACK_SRC 不像 gstack 仓库，先跑 git submodule update --init" >&2
  exit 1
}

broken_total=0

install_into() {
  local skills_dir="$1"
  local gstack_link="$skills_dir/gstack"
  local linked=()

  echo "── $skills_dir"
  mkdir -p "$skills_dir"

  # ─── 总入口软链 ────────────────────────────────────────────
  # 三个 SKILL.md 内部把 ~/.claude/skills/gstack/bin/... 和 ETHOS.md 写死了，
  # 这个软链让那些绝对路径解析得到，磁盘上仍然只有 submodule 一份。
  if [ -L "$gstack_link" ]; then
    local cur; cur="$(readlink "$gstack_link")"
    if [ "$cur" != "$GSTACK_SRC" ]; then
      echo "   刷新入口软链：$cur -> $GSTACK_SRC"
      rm -f "$gstack_link"
      ln -s "$GSTACK_SRC" "$gstack_link"
    fi
  elif [ -e "$gstack_link" ]; then
    echo "错误：$gstack_link 已存在且不是软链（可能是独立 clone）。" >&2
    echo "      先移走它，或改用 gstack 官方 ./setup --prefix。" >&2
    exit 1
  else
    echo "   建立入口软链：$gstack_link -> $GSTACK_SRC"
    ln -s "$GSTACK_SRC" "$gstack_link"
  fi

  # ─── 逐个 skill 建外壳目录 ─────────────────────────────────
  # Claude Code 只扫 <skills_dir>/<名字>/SKILL.md 这一层，不递归，
  # 所以必须是真实目录加内部软链，不能整个目录软链过去。
  local name src skill_name link_name dst asset a
  for name in "${WANTED[@]}"; do
    src="$GSTACK_SRC/$name"
    if [ ! -f "$src/SKILL.md" ]; then
      echo "   跳过 $name：上游已不存在或改名" >&2
      continue
    fi

    # 目录名以 frontmatter 的 name: 为准，与 setup 一致
    skill_name="$(grep -m1 '^name:' "$src/SKILL.md" | sed 's/^name:[[:space:]]*//' | tr -d '[:space:]')"
    [ -n "$skill_name" ] || skill_name="$name"
    case "$skill_name" in
      gstack-*) link_name="$skill_name" ;;
      *)        link_name="gstack-$skill_name" ;;
    esac

    dst="$skills_dir/$link_name"
    [ -L "$dst" ] && rm -f "$dst"   # 旧版整目录软链，升级掉
    mkdir -p "$dst"

    rm -rf "$dst/SKILL.md"
    ln -s "$gstack_link/$name/SKILL.md" "$dst/SKILL.md"

    # SKILL.md 之外的同级资源全链过去，排除项与 setup 保持一致
    for asset in "$src"/*; do
      [ -e "$asset" ] || continue
      a="$(basename "$asset")"
      case "$a" in
        SKILL.md|node_modules|dist|test|*.tmpl) continue ;;
      esac
      rm -rf "${dst:?}/$a"
      ln -s "$gstack_link/$name/$a" "$dst/$a"
    done

    linked+=("$link_name")
  done

  echo "   已链接：${linked[*]:-（无）}"

  # ─── 清理 WANTED 之外的 gstack-* 残留 ──────────────────────
  local d b keep l
  if [ "$PRUNE" -eq 1 ]; then
    for d in "$skills_dir"/gstack-*; do
      [ -e "$d" ] || continue
      b="$(basename "$d")"
      keep=0
      for l in "${linked[@]:-}"; do [ "$b" = "$l" ] && keep=1; done
      [ "$keep" -eq 1 ] && continue
      echo "   清理：$b"
      rm -rf "$d"
    done
  fi

  # ─── 断链自检 ──────────────────────────────────────────────
  # 入口软链自身也查，它断了三个包装目录会跟着全断。
  local f
  if [ ! -e "$gstack_link" ]; then
    echo "   断链：$gstack_link" >&2
    broken_total=$((broken_total + 1))
  fi
  for l in "${linked[@]:-}"; do
    while IFS= read -r f; do
      echo "   断链：$f" >&2
      broken_total=$((broken_total + 1))
    done < <(find "$skills_dir/$l" -maxdepth 1 -type l ! -exec test -e {} \; -print 2>/dev/null)
  done
}

install_into "$HOME/.claude/skills"

if [ -d "$HOME/.agents/skills" ]; then
  install_into "$HOME/.agents/skills"
else
  echo "── $HOME/.agents/skills 不存在，跳过"
fi

[ "$broken_total" -eq 0 ] && echo "自检通过，无断链。" || {
  echo "自检发现 $broken_total 处断链。" >&2
  exit 1
}
