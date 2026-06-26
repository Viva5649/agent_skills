#!/usr/bin/env python3
"""Scan recent X posts from target creator accounts.

Default pipeline:
- Fetch recent account timelines through the local X API backend (fetch_x_posts.py)
- Score and filter posts into creator-signal candidates

Optional fallback backends:
- opencli-google/opencli-twitter: discover candidate post URLs via opencli
- syndication: public X timeline widget discovery fallback
- oEmbed: read public post text for URL-based discovery backends
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import shutil
import subprocess
import time
import sys
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests


KW = [
    "tool",
    "workflow",
    "method",
    "tutorial",
    "prompt",
    "template",
    "framework",
    "automation",
    "agent",
    "creator",
    "startup",
    "business",
    "monetize",
    "revenue",
    "pricing",
    "distribution",
    "positioning",
    "insight",
    "trend",
    "model",
    "platform",
]
EXCLUDE_HINTS = [
    "gpu",
    "tpu",
    "datacenter",
    "data center",
    "cybersecurity",
    "security vulnerability",
    "tokenomics",
]
WEAK_NEGATIVE_HINTS = ["benchmark", "funding", "raised", "valuation", "acquisition"]
SIGNAL_HINTS = {
    "practical": [
        "tool",
        "workflow",
        "tutorial",
        "prompt",
        "template",
        "guide",
        "how to",
        "step",
        "automation",
        "agent",
    ],
    "opportunity": [
        "startup",
        "business",
        "monetize",
        "revenue",
        "pricing",
        "customer",
        "distribution",
        "positioning",
        "market",
        "side project",
    ],
    "cognition": [
        "framework",
        "principle",
        "mindset",
        "lesson",
        "mistake",
        "insight",
        "strategy",
        "taste",
        "judgment",
    ],
    "trend": [
        "trend",
        "model",
        "platform",
        "release",
        "ecosystem",
        "capability",
        "adoption",
        "frontier",
        "benchmark",
    ],
}
DISCOVER_BACKENDS = ("opencli-google", "opencli-twitter", "syndication")
FETCH_BACKENDS = ("oembed",)
DEFAULT_TIMEOUT = 30


class ConfigurationError(RuntimeError):
    """User-fixable runtime configuration problem."""




def load_keywords_config(path: str) -> dict:
    """Load keyword/hint configuration from a JSON file."""
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


STATUS_RE = re.compile(r"https?://(?:www\.)?(?:x|twitter)\.com/([^/]+)/status/(\d+)", re.IGNORECASE)
STATUS_ID_RE = re.compile(
    r"https?://(?:www\.)?(?:x|twitter)\.com/(?:[^/]+|i)/status/(\d+)", re.IGNORECASE
)
MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]+\)")
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
HTML_TAG_RE = re.compile(r"<[^>]+>")
OEMBED_PARAGRAPH_RE = re.compile(r"<p\b[^>]*>(.*?)</p>", re.IGNORECASE | re.DOTALL)
NEXT_DATA_RE = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>')
REPLY_COUNT_RE = re.compile(r"^Read \d+ replies$")
ENGAGEMENT_RE = re.compile(r"^[\d.,]+[KMB]?$", re.IGNORECASE)
READ_ONLY_OPENCLI_COMMANDS = {
    ("twitter", "search"),
    ("google", "search"),
    ("profile", "list"),
}
# Known opencli first-level subcommand groups (appear after global flags like --profile)
KNOWN_OPENCLI_GROUPS = {"twitter", "google", "browser", "plugin", "adapter", "profile", "daemon"}


def log(message: str) -> None:
    print(f"[creator-signal-digest] {message}", file=sys.stderr)


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def run_opencli_read_only(
    args: List[str],
    extra_env: Dict[str, str] | None = None,
    timeout: int | None = None,
) -> str:
    if len(args) < 3 or args[0] != "opencli":
        raise ValueError("opencli command must start with: opencli <group> <command>")

    # Find group/command position, skipping global flags like --profile <name>
    group_idx = None
    for i in range(1, len(args) - 1):
        if args[i] in KNOWN_OPENCLI_GROUPS:
            group_idx = i
            break

    if group_idx is None or group_idx + 1 >= len(args):
        raise ValueError(f"opencli command missing known group: {' '.join(args)}")

    command_key = (args[group_idx], args[group_idx + 1])
    if command_key not in READ_ONLY_OPENCLI_COMMANDS:
        raise ValueError(f"unsafe opencli command blocked: {' '.join(args[:group_idx+2])}")

    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(args, text=True, capture_output=True, check=False, env=env, timeout=timeout)
    output = proc.stdout
    if proc.stderr:
        output = f"{output}\n{proc.stderr}" if output else proc.stderr

    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, args, output=output)
    return output


def extract_first_json_value(raw: str) -> Any:
    text = raw.lstrip()
    if not text:
        raise ValueError("empty output")

    decoder = json.JSONDecoder()
    return decoder.raw_decode(text)[0]


def clean_extracted_text(text: str) -> str:
    text = MARKDOWN_IMAGE_RE.sub("", text)
    text = MARKDOWN_LINK_RE.sub(r"\1", text)

    out_lines: List[str] = []
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            if out_lines and out_lines[-1] != "":
                out_lines.append("")
            continue
        if line.startswith(("Published Time:", "URL Source:", "Markdown Content:")):
            continue
        if line in ("[]",):
            continue
        if REPLY_COUNT_RE.match(line):
            continue
        if ENGAGEMENT_RE.match(line):
            continue
        if line.lower() in ("post", "conversation", "see new posts", "sign up"):
            continue
        out_lines.append(line)
    return "\n".join(out_lines).strip()


def strip_html_fragment(fragment: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.IGNORECASE)
    text = HTML_TAG_RE.sub("", text)
    text = html.unescape(text).replace("\xa0", " ")
    return clean_extracted_text(text)


def normalize_status_url(url: str, preferred_handle: str | None = None) -> str | None:
    match = STATUS_RE.search(url or "")
    if match and match.group(1).lower() != "i":
        return f"https://x.com/{match.group(1)}/status/{match.group(2)}"

    id_match = STATUS_ID_RE.search(url or "")
    if not id_match:
        return None

    if preferred_handle:
        return f"https://x.com/{preferred_handle}/status/{id_match.group(1)}"
    return f"https://x.com/i/status/{id_match.group(1)}"


def extract_status_url(url: str, preferred_handle: str | None = None) -> str | None:
    return normalize_status_url(url, preferred_handle=preferred_handle)


def parse_dateish(value: str | None) -> dt.date | None:
    if not value:
        return None

    text = html.unescape(value).strip()
    text = re.sub(r"\s+", " ", text)
    if not text:
        return None

    for fmt in (
        "%Y-%m-%d",
        "%B %d, %Y",
        "%b %d, %Y",
        "%I:%M %p · %b %d, %Y",
        "%I:%M %p · %B %d, %Y",
    ):
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            pass

    try:
        return parsedate_to_datetime(text).date()
    except (TypeError, ValueError, IndexError):
        pass

    try:
        return dt.datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def keyword_hint_regex() -> re.Pattern[str]:
    return re.compile(r"\b(" + "|".join(re.escape(kw) for kw in KW) + r")\b", re.IGNORECASE)


KW_HINT_RE = keyword_hint_regex()


def has_cjk(text: str) -> bool:
    """Detect Chinese/Japanese/Korean characters in text."""
    return bool(re.search(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]', text))


def signal_tags(text: str) -> List[str]:
    lowered = text.lower()
    tags = []
    for tag, hints in SIGNAL_HINTS.items():
        if any(hint.lower() in lowered for hint in hints):
            tags.append(tag)
    return tags


def looks_signal_worthy(text: str) -> bool:
    lowered = text.lower()
    if KW_HINT_RE.search(text):
        return True

    # English signal markers
    if any(
        marker in lowered
        for marker in (
            "here's",
            "here is",
            "how to",
            "step-by-step",
            "what this means",
            "why this matters",
            "new opportunity",
            "use case",
        )
    ):
        return True

    # Chinese signal markers
    if has_cjk(text) and any(
        marker in text
        for marker in (
            "步骤", "教程", "指南", "实操", "上手", "复现",
            "副业", "变现", "一人公司", "出海",
            "怎么", "如何", "Prompt", "模板", "工具",
            "方法论", "认知", "思维", "复盘",
            "开源", "趋势", "工作流", "Agent",
        )
    ):
        return True

    return False


def score_text(text: str) -> int:
    """Score candidate text for signal density.

    Uses the globally-configured KW, SIGNAL_HINTS, EXCLUDE_HINTS, and
    WEAK_NEGATIVE_HINTS lists so that keyword-config overrides (e.g.
    keywords_zh.json) are reflected in scoring.
    """
    t = text.lower()
    score = 0
    cjk = has_cjk(text)

    # ---- Universal heuristics (language-independent) ----
    # Numbered/bulleted structure signal
    if re.search(r"\b\d\)\b|\b\d\.\b", t):
        score += 2

    # Matches against the configured KW list (each hit +1)
    for kw in KW:
        if kw.lower() in t:
            score += 1

    # Signal-tag matches (double-weight vs raw keyword matches)
    score += len(signal_tags(text)) * 2

    # ---- English-specific heuristics ----
    if "here's" in t or "here is" in t:
        score += 3
    if "step" in t or "steps" in t:
        score += 3
    if "prompt" in t:
        score += 3
    if "template" in t:
        score += 2
    if "workflow" in t:
        score += 2
    if "how to" in t:
        score += 2
    if "framework" in t or "principle" in t:
        score += 2
    if "startup" in t or "business" in t or "monetize" in t:
        score += 2
    if "revenue" in t or "pricing" in t or "distribution" in t:
        score += 2
    if "trend" in t or "platform" in t or "ecosystem" in t:
        score += 2
    if "model" in t or "capability" in t:
        score += 1
    if "open source" in t or "oss" in t:
        score += 2

    # ---- Chinese-specific heuristics ----
    if cjk:
        # High-signal: actionable / tutorial
        if "步骤" in t or "教程" in t or "指南" in t:
            score += 3
        if "实操" in t or "上手" in t or "复现" in t:
            score += 3
        if "怎么" in t or "如何" in t:
            score += 2

        # High-signal: opportunity / monetization
        if "副业" in t or "变现" in t:
            score += 3
        if "一人公司" in t or "出海" in t:
            score += 2

        # High-signal: cognition
        if "方法论" in t or "认知" in t:
            score += 2
        if "复盘" in t or "思维" in t:
            score += 2

        # Medium-signal: trend / tooling
        if "开源" in t or "open source" in t:
            score += 2
        if "Prompt" in text:  # case-sensitive: Chinese community writes "Prompt" capitalized
            score += 3
        if "模板" in t:
            score += 2
        if "工作流" in t:
            score += 2

    # ---- Penalties ----
    if "reposted" in t[:120]:
        score -= 2
    for bad in EXCLUDE_HINTS:
        if bad.lower() in t:
            score -= 3
    for weak_bad in WEAK_NEGATIVE_HINTS:
        safe_words = ("why", "means", "opportunity", "watch",
                      "为什么", "意味着", "机会", "值得")
        if weak_bad.lower() in t and not any(good in t for good in safe_words):
            score -= 1

    # Length bonus (longer posts tend to carry more signal)
    score += min(len(t) // 240, 3)

    return score


def is_noisy_candidate(text: str) -> bool:
    """Filter out obvious noise: pure links, empty/placeholder content,
    single-sentence throwaway remarks, and pure reposts."""
    # Strip URLs and media-only links for text-only analysis
    cleaned = re.sub(r'(?:https?://\S+|pic\.twitter\.com/\S+)', '', text).strip()
    # Also strip common noise prefixes
    cleaned = re.sub(r'^pic\.twitter\.com/\S+', '', cleaned).strip()

    # 1. Nearly empty after URL removal (pure link posts)
    #    Threshold is deliberately low (20 chars) so short-but-signal-bearing
    #    tweets like "小红书已上架Red Skill，有人月入上千" survive for LLM review.
    if len(cleaned) < 20:
        return True

    # 2. Very short single-sentence with no structure markers -- likely throwaway
    if len(cleaned) < 60 and not re.search(r'[。！？.!?，、：；]', cleaned):
        return True

    # 3. Chinese throwaway remarks (e.g. "多出去走走，其实没有 agent 生活并不会怎么样")
    if has_cjk(text) and len(cleaned) < 100:
        throwaway = [
            r'^多.*其实.*并不会怎么样',
            r'^.*了解一下$',
        ]
        for pat in throwaway:
            if re.search(pat, cleaned) and len(cleaned) < 80:
                return True

    # 4. Pure forwarded content / repost with zero added commentary
    if re.match(r'^(转发|转[发帖]|Repost|RT)\b', cleaned.strip()):
        return True

    # 5. Text that's mostly @-mentions / hashtags with negligible real content
    mentions_stripped = re.sub(r'[#@]\w+', '', cleaned).strip()
    if len(mentions_stripped) < 15 and len(cleaned) > 20:
        return True

    return False


def parse_syndication_timeline_html(html_text: str) -> Dict[str, Any]:
    match = NEXT_DATA_RE.search(html_text)
    if not match:
        raise ValueError("syndication payload missing __NEXT_DATA__")
    payload = json.loads(html.unescape(match.group(1)))
    page_props = payload["props"]["pageProps"]
    context = page_props.get("contextProvider") or {}
    timeline = page_props.get("timeline") or {}
    return {
        "has_results": bool(context.get("hasResults")),
        "entries": timeline.get("entries") or [],
        "latest_tweet_id": timeline.get("latest_tweet_id"),
    }


def fetch_syndication_timeline(handle: str, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    response = requests.get(
        f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{handle}",
        params={"lang": "en", "showHeader": "true", "showReplies": "false", "transparent": "false"},
        headers={"User-Agent": "creator-signal-digest/1.0"},
        timeout=timeout,
    )
    response.raise_for_status()
    return parse_syndication_timeline_html(response.text)


def build_opencli_twitter_queries(handle: str, after: str) -> List[str]:
    keyword_clause = " OR ".join(KW)
    return [
        f"from:{handle} ({keyword_clause}) since:{after}",
        f"from:{handle} since:{after}",
    ]


def run_opencli_twitter_search(query: str, limit: int = 20, profile: str | None = None) -> List[Dict[str, Any]]:
    if not command_exists("opencli"):
        raise FileNotFoundError("opencli not found")

    cmd = ["opencli"]
    if profile:
        cmd.extend(["--profile", profile])
    cmd.extend([
        "twitter",
        "search",
        "--filter",
        "top",
        "-f",
        "json",
        "--limit",
        str(limit),
        query,
    ])
    try:
        output = run_opencli_read_only(cmd)
    except subprocess.CalledProcessError as exc:
        if "No search results found" in (exc.output or ""):
            return []
        raise

    data = extract_first_json_value(output)
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def run_opencli_google_search(query: str, limit: int = 20, lang: str = "en", profile: str | None = None) -> List[Dict[str, Any]]:
    if not command_exists("opencli"):
        raise FileNotFoundError("opencli not found")

    cmd = ["opencli"]
    if profile:
        cmd.extend(["--profile", profile])
    cmd.extend([
        "google",
        "search",
        "-f",
        "json",
        "--limit",
        str(limit),
        "--lang",
        lang,
        query,
    ])
    try:
        output = run_opencli_read_only(cmd)
    except subprocess.CalledProcessError as exc:
        if "No search results found" in (exc.output or ""):
            return []
        raise
    data = extract_first_json_value(output)
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def chunk(items: List[str], size: int) -> List[List[str]]:
    if size <= 0:
        size = 1
    return [items[index : index + size] for index in range(0, len(items), size)]


def required_profile_count(handle_count: int, accounts_per_profile: int) -> int:
    if handle_count <= 0:
        return 0
    return (handle_count + accounts_per_profile - 1) // accounts_per_profile


def discover_urls_syndication(
    handles: List[str],
    cutoff_date: dt.date,
    timeout: int,
    require_signal: bool,
) -> List[str]:
    urls: List[str] = []
    for idx, handle in enumerate(handles, 1):
        try:
            payload = fetch_syndication_timeline(handle, timeout=timeout)
        except (requests.RequestException, ValueError) as exc:
            log(f"warn: syndication user {idx}/{len(handles)} @{handle} failed: {exc}")
            continue

        entries = payload.get("entries") or []
        user_hits = 0
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("type") != "tweet":
                continue
            content = entry.get("content") or {}
            tweet = content.get("tweet") or {}
            if not isinstance(tweet, dict):
                continue
            created_date = parse_dateish(str(tweet.get("created_at") or ""))
            if created_date and created_date < cutoff_date:
                continue
            text = clean_extracted_text(str(tweet.get("full_text") or tweet.get("text") or ""))
            if require_signal and text and not looks_signal_worthy(text):
                continue
            permalink = tweet.get("permalink")
            if isinstance(permalink, str) and permalink.strip():
                normalized = normalize_status_url("https://x.com" + permalink)
                if normalized:
                    urls.append(normalized)
                    user_hits += 1
        log(f"syndication user {idx}/{len(handles)} @{handle} -> {user_hits} urls")
    return urls


def parse_opencli_profile_list(raw: str) -> List[str]:
    profiles: List[str] = []
    raw_lines = 0
    empty_profile_lines = 0
    no_profile_messages = (
        "no profiles",
        "no profile",
        "no connected profiles",
        "no connected profile",
        "no browser bridge profiles",
        "no browser bridge profile",
        "0 profiles",
        "0 profile",
    )
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        raw_lines += 1
        lowered = stripped.lower()
        if any(message in lowered for message in no_profile_messages):
            empty_profile_lines += 1
            continue
        # Format: "  profile_name \u2014 connected v1.2.3" or "  profile_name - connected ..."
        for sep in (" \u2014 ", " \u2014", " - "):
            if sep in stripped:
                name = stripped.split(sep)[0].strip()
                if name:
                    profiles.append(name)
                break

    if profiles or raw_lines == 0 or empty_profile_lines == raw_lines:
        return profiles

    raise ConfigurationError(
        "opencli profile list returned output but no profiles could be parsed; "
        "the output format may have changed. "
        f"Raw output first lines: {chr(10).join(raw.splitlines()[:5])}"
    )


def detect_opencli_profiles() -> List[str]:
    """Auto-detect connected Browser Bridge profiles via `opencli profile list`."""
    try:
        output = run_opencli_read_only(["opencli", "profile", "list"], timeout=10)
    except FileNotFoundError as exc:
        raise ConfigurationError("opencli not found while detecting profiles") from exc
    except subprocess.TimeoutExpired as exc:
        raise ConfigurationError("opencli profile list timed out while detecting profiles") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.output or "").strip()
        message = "opencli profile list failed while detecting profiles"
        if detail:
            message = f"{message}: {detail}"
        raise ConfigurationError(message) from exc

    return parse_opencli_profile_list(output)


def discover_urls_opencli(
    handles: List[str],
    after: str,
    _batch_size: int,
    per_search: int,
    _lang: str,
    cutoff_date: dt.date,
    require_signal: bool,
) -> List[str]:
    urls: List[str] = []
    success_users = 0
    failed_users = 0
    signal_groups = {
        name: " OR ".join(hints)
        for name, hints in SIGNAL_HINTS.items()
    }

    # Load Chrome Profile rotation list.
    # Priority: env var OPENCLI_CHROME_PROFILES > auto-detect via `opencli profile list`
    profiles_raw = os.environ.get("OPENCLI_CHROME_PROFILES", "")
    profiles = [p.strip() for p in profiles_raw.split(",") if p.strip()]
    if not profiles:
        profiles = detect_opencli_profiles()
        if profiles:
            log(f"opencli auto-detected {len(profiles)} profile(s): {', '.join(profiles)}")
    if not profiles:
        log("warn: no profiles configured (set OPENCLI_CHROME_PROFILES=profile1,profile2 or ensure opencli profile list returns profiles); "
            "all searches will use the default opencli profile")
    ACCOUNTS_PER_PROFILE = 10
    if profiles:
        required_profiles = required_profile_count(len(handles), ACCOUNTS_PER_PROFILE)
        if len(profiles) < required_profiles:
            raise ConfigurationError(
                "opencli profile count insufficient: "
                f"accounts={len(handles)}, accounts_per_profile={ACCOUNTS_PER_PROFILE}, "
                f"profiles={len(profiles)}, required_profiles={required_profiles}. "
                "Add more profiles to OPENCLI_CHROME_PROFILES, connect more Browser Bridge profiles, "
                "or reduce the accounts file before running opencli-twitter discovery."
            )

    for idx, handle in enumerate(handles, 1):
        user_hits = 0
        seen_for_user = set()
        query_errors: List[str] = []

        # Determine which Chrome Profile to use for this user
        current_profile: str | None = None
        if profiles:
            profile_index = (idx - 1) // ACCOUNTS_PER_PROFILE
            current_profile = profiles[profile_index]
            if idx == 1 or profile_index != (idx - 2) // ACCOUNTS_PER_PROFILE:
                log(f"opencli switching to profile: {current_profile} (slot {profile_index + 1}/{len(profiles)})")

        # Rounds 1-4: keyword queries by signal group (split to avoid 429 on long query strings)
        for group_name, group_clause in signal_groups.items():
            if user_hits >= per_search:
                break
            try:
                kw_query = f"from:{handle} ({group_clause}) since:{after}"
                results = run_opencli_twitter_search(kw_query, limit=per_search, profile=current_profile)
                for result in results:
                    author = str(result.get("author") or "").strip()
                    normalized = extract_status_url(str(result.get("url", "")), preferred_handle=author or handle)
                    if not normalized:
                        continue
                    match = STATUS_RE.search(normalized)
                    if not match or match.group(1).lower() != handle.lower():
                        continue
                    created_date = parse_dateish(str(result.get("created_at") or ""))
                    if created_date and created_date < cutoff_date:
                        continue
                    text = clean_extracted_text(str(result.get("text") or ""))
                    if require_signal and text and not looks_signal_worthy(text):
                        continue
                    if normalized in seen_for_user:
                        continue
                    seen_for_user.add(normalized)
                    urls.append(normalized)
                    user_hits += 1
                log(f"opencli user {idx}/{len(handles)} @{handle} keyword[{group_name}] -> {len(results)} results")
            except (subprocess.CalledProcessError, ValueError) as exc:
                query_errors.append(f"keyword[{group_name}]: {exc}")
                log(f"warn: opencli user {idx}/{len(handles)} @{handle} keyword[{group_name}] failed: {exc}")

            time.sleep(2)  # throttle between signal-group queries

        # Round 5: bare query (fallback supplement)
        if user_hits < per_search:
            try:
                bare_query = f"from:{handle} since:{after}"
                bare_limit = max(1, per_search - user_hits)
                results = run_opencli_twitter_search(bare_query, limit=bare_limit, profile=current_profile)
                for result in results:
                    author = str(result.get("author") or "").strip()
                    normalized = extract_status_url(str(result.get("url", "")), preferred_handle=author or handle)
                    if not normalized:
                        continue
                    match = STATUS_RE.search(normalized)
                    if not match or match.group(1).lower() != handle.lower():
                        continue
                    if normalized in seen_for_user:
                        continue
                    created_date = parse_dateish(str(result.get("created_at") or ""))
                    if created_date and created_date < cutoff_date:
                        continue
                    text = clean_extracted_text(str(result.get("text") or ""))
                    if require_signal and text and not looks_signal_worthy(text):
                        continue
                    seen_for_user.add(normalized)
                    urls.append(normalized)
                    user_hits += 1
                log(f"opencli user {idx}/{len(handles)} @{handle} bare -> {len(results)} results")
            except (subprocess.CalledProcessError, ValueError) as exc:
                query_errors.append(f"bare: {exc}")
                log(f"warn: opencli user {idx}/{len(handles)} @{handle} bare failed: {exc}")

        # Only mark failed if both rounds produced zero hits AND had errors
        if user_hits > 0 or not query_errors:
            success_users += 1
        else:
            failed_users += 1
        log(
            f"opencli user {idx}/{len(handles)} @{handle} -> {user_hits} urls "
            f"(total_urls={len(urls)} success_users={success_users} failed_users={failed_users})"
        )

        if idx < len(handles):
            time.sleep(15)

    return urls


def discover_urls_opencli_google(
    handles: List[str],
    after: str,
    batch_size: int,
    per_search: int,
    lang: str,
    _cutoff_date: dt.date,
    require_signal: bool,
) -> List[str]:
    urls: List[str] = []
    success_batches = 0
    failed_batches = 0

    # Detect Browser Bridge profiles for --profile passthrough.
    # Google search is less rate-limited than Twitter, but when multiple
    # profiles are connected, opencli requires an explicit --profile.
    profiles_raw = os.environ.get("OPENCLI_CHROME_PROFILES", "")
    profiles = [p.strip() for p in profiles_raw.split(",") if p.strip()]
    if not profiles:
        try:
            profiles = detect_opencli_profiles()
        except ConfigurationError:
            profiles = []
    if profiles:
        log(f"google detected {len(profiles)} profile(s): {', '.join(profiles)}")
    else:
        log("warn: no profiles configured for google search; may fail with multiple connected profiles")

    for batch_index, handle_batch in enumerate(chunk(handles, batch_size), 1):
        lower_handles = {handle.lower() for handle in handle_batch}
        user_hits = 0
        seen_for_batch = set()
        sites = " OR ".join(f"site:x.com/{handle}/status" for handle in handle_batch)
        keyword_clause = " OR ".join(KW)
        queries = [
            f"({sites}) ({keyword_clause}) after:{after}",
            f"({sites}) after:{after}",
        ]

        # Profile selection with retry: try each profile in round-robin order
        # until one succeeds or all are exhausted.
        profile_order: List[str | None]
        if profiles:
            start_idx = (batch_index - 1) % len(profiles)
            profile_order = [profiles[(start_idx + offset) % len(profiles)] for offset in range(len(profiles))]
        else:
            profile_order = [None]

        batch_succeeded = False
        last_error: Exception | None = None
        tried_profiles: List[str] = []

        for attempt_profile in profile_order:
            if batch_succeeded:
                break
            try:
                for query_index, query in enumerate(queries, 1):
                    results = run_opencli_google_search(query, limit=per_search, lang=lang, profile=attempt_profile)
                    for result in results:
                        normalized = extract_status_url(str(result.get("url") or ""))
                        if not normalized:
                            continue

                        match = STATUS_RE.search(normalized)
                        if not match or match.group(1).lower() not in lower_handles:
                            continue

                        text = clean_extracted_text(
                            f"{str(result.get('title') or '')}\n{str(result.get('snippet') or result.get('description') or '')}"
                        )
                        if require_signal and text and not looks_signal_worthy(text):
                            continue

                        if normalized in seen_for_batch:
                            continue

                        seen_for_batch.add(normalized)
                        urls.append(normalized)
                        user_hits += 1

                    log(f"google batch {batch_index} query#{query_index} (profile={attempt_profile}) -> {len(results)} results")
                    if user_hits >= per_search:
                        break
                batch_succeeded = True
            except (subprocess.CalledProcessError, ValueError) as exc:
                last_error = exc
                tried_profiles.append(str(attempt_profile))
                log(f"warn: google batch {batch_index} profile={attempt_profile} failed: {exc}; trying next profile")
                # Small delay before retry with next profile
                time.sleep(2)

        if not batch_succeeded:
            failed_batches += 1
            log(
                f"warn: google batch {batch_index} failed after trying profiles={tried_profiles}: {last_error} "
                f"(total_urls={len(urls)} success_batches={success_batches} failed_batches={failed_batches})"
            )
            continue

        success_batches += 1
        log(
            f"google batch {batch_index} handles={len(handle_batch)} -> {user_hits} urls "
            f"(total_urls={len(urls)} success_batches={success_batches} failed_batches={failed_batches})"
        )
    return urls


def minimum_auto_urls(handle_count: int, per_search: int) -> int:
    return max(10, min(handle_count, per_search))


def dedupe_urls(urls: Iterable[str]) -> List[str]:
    seen = set()
    unique: List[str] = []
    for url in urls:
        normalized = normalize_status_url(url)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
    return unique


def discover_status_urls(
    backend: str,
    handles: List[str],
    after: str,
    cutoff_date: dt.date,
    batch_size: int,
    per_search: int,
    lang: str,
    timeout: int,
    require_signal: bool,
) -> Dict[str, str]:
    target_urls = minimum_auto_urls(len(handles), per_search)
    discovered: Dict[str, str] = {}
    backends = [backend] if backend != "auto" else list(DISCOVER_BACKENDS)

    for raw_name in backends:
        name = "opencli-twitter" if raw_name == "opencli" else raw_name
        try:
            if name == "syndication":
                urls = discover_urls_syndication(handles, cutoff_date, timeout, require_signal=require_signal)
            elif name == "opencli-twitter":
                urls = discover_urls_opencli(
                    handles,
                    after,
                    batch_size,
                    per_search,
                    lang,
                    cutoff_date,
                    require_signal=require_signal,
                )
            elif name == "opencli-google":
                urls = discover_urls_opencli_google(
                    handles,
                    after,
                    batch_size,
                    per_search,
                    lang,
                    cutoff_date,
                    require_signal=require_signal,
                )
            else:
                raise ValueError(f"unsupported discover backend: {raw_name}")
        except (FileNotFoundError, requests.RequestException, subprocess.CalledProcessError, ValueError) as exc:
            log(f"warn: discover backend {raw_name} failed: {exc}")
            urls = []

        before = len(discovered)
        for url in dedupe_urls(urls):
            discovered.setdefault(url, name)
        added = len(discovered) - before
        log(f"discover backend {raw_name} added {added} urls (total={len(discovered)})")

        if backend == "auto" and len(discovered) >= target_urls:
            break

    return discovered


def parse_oembed_payload(payload: Dict[str, Any]) -> Dict[str, str | None]:
    html_fragment = str(payload.get("html", "")).strip()
    if not html_fragment:
        raise ValueError("oEmbed response missing html")

    paragraph_match = OEMBED_PARAGRAPH_RE.search(html_fragment)
    if not paragraph_match:
        raise ValueError("oEmbed html missing paragraph")

    text = strip_html_fragment(paragraph_match.group(1))
    if not text:
        raise ValueError("oEmbed text extraction failed")

    published_date = None
    for anchor_text in reversed(re.findall(r"<a\b[^>]*>(.*?)</a>", html_fragment, flags=re.IGNORECASE | re.DOTALL)):
        parsed = parse_dateish(strip_html_fragment(anchor_text))
        if parsed:
            published_date = parsed.isoformat()
            break

    return {
        "text": text,
        "author_name": str(payload.get("author_name") or "").strip() or None,
        "published_date": published_date,
        "canonical_url": normalize_status_url(str(payload.get("url") or "")),
    }


def fetch_tweet_oembed(status_url: str, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, str | None]:
    response = requests.get(
        "https://publish.x.com/oembed",
        params={"url": status_url, "omit_script": "1"},
        headers={"User-Agent": "creator-signal-digest/1.0"},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("unexpected oEmbed payload")
    info = parse_oembed_payload(payload)
    info["backend"] = "oembed"
    return info


def fetch_tweet_info(status_url: str, backend: str, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, str | None]:
    if backend not in ("auto", "oembed"):
        raise ValueError(f"unsupported fetch backend: {backend}")
    try:
        return fetch_tweet_oembed(status_url, timeout=timeout)
    except (requests.RequestException, ValueError) as exc:
        raise RuntimeError(f"oembed: {exc}") from exc


def load_handles(accounts_path: Path) -> List[str]:
    handles: List[str] = []
    for line in accounts_path.read_text("utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        handles.append(stripped.lstrip("@"))
    return handles


def load_seed_urls(seed_path: Path) -> Dict[str, str]:
    discovered: Dict[str, str] = {}
    for line in seed_path.read_text("utf-8").splitlines():
        normalized = normalize_status_url(line.strip())
        if normalized:
            discovered[normalized] = "seed"
    return discovered


def _get_env_zsh(env_name: str) -> Optional[str]:
    """Try process env first, then interactive zsh (for ~/.zshrc credentials)."""
    value = os.environ.get(env_name)
    if value:
        return value
    try:
        result = subprocess.run(
            ["zsh", "-ic", "env"],
            capture_output=True, text=True, check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    for line in result.stdout.splitlines():
        if line.startswith(f"{env_name}="):
            return line.split("=", 1)[1]
    return None


def resolve_x_api_backend_name(name: str) -> str:
    """Resolve auto selection using the same priority as fetch_x_posts."""
    if name != "auto":
        return name
    if _get_env_zsh("GETX_API_KEY"):
        return "getxapi"
    if _get_env_zsh("TWITTERAPI_IO_KEY"):
        return "twitterapiio"
    if _get_env_zsh("X_BEARER_TOKEN"):
        return "official"
    return "auto"


def _load_x_posts_module() -> Any:
    """Load the local fetch_x_posts module (independent copy, originally from tech-news-digest)."""
    import fetch_x_posts
    return fetch_x_posts


def build_x_api_sources(handles: List[str]) -> List[Dict[str, Any]]:
    sources: List[Dict[str, Any]] = []
    for handle in handles:
        clean_handle = handle.lstrip("@")
        sources.append(
            {
                "id": f"{clean_handle.lower()}-creator-x",
                "type": "twitter",
                "name": clean_handle,
                "handle": clean_handle,
                "enabled": True,
                "priority": False,
                "topics": [],
            }
        )
    return sources


def fetch_candidates_x_api(
    handles: List[str],
    days: int,
    cutoff_date: dt.date,
    x_api_backend: str,
    require_signal: bool,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    resolved_backend = resolve_x_api_backend_name(x_api_backend)
    if resolved_backend == "auto":
        raise ConfigurationError(
            "x-api discovery requires GETX_API_KEY, TWITTERAPI_IO_KEY, or X_BEARER_TOKEN"
        )

    fetch_x = _load_x_posts_module()
    if hasattr(fetch_x, "setup_logging"):
        fetch_x.setup_logging(False)
    backend = fetch_x.select_backend(resolved_backend)
    if backend is None:
        raise ConfigurationError(f"x-api backend unavailable: {resolved_backend}")

    cutoff_dt = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    sources = build_x_api_sources(handles)
    log(f"x-api fetching {len(sources)} accounts with backend={resolved_backend}")
    try:
        results = backend.fetch_all(sources, cutoff_dt)
    except Exception as exc:
        log(f"warn: x-api backend failed for all accounts: {exc}")
        return [], handles[:]

    candidates: List[Dict[str, Any]] = []
    failed_handles: List[str] = []
    result_handles = set()
    fetched_at = dt.datetime.now().isoformat(timespec="seconds")
    for result in results:
        handle = str(result.get("handle") or "").lstrip("@")
        if handle:
            result_handles.add(handle.lower())
        if result.get("status") != "ok":
            log(f"warn: x-api @{handle} failed: {result.get('error', 'unknown')}")
            if handle:
                failed_handles.append(handle)
            continue

        for article in result.get("articles") or []:
            text = str(article.get("title") or "").strip()
            if not text:
                continue
            if require_signal and not looks_signal_worthy(text):
                continue

            published_date = parse_dateish(str(article.get("date") or ""))
            if published_date and published_date < cutoff_date:
                continue

            raw_url = str(article.get("link") or "")
            canonical_url = normalize_status_url(raw_url, preferred_handle=handle) or raw_url
            if not canonical_url:
                continue

            candidates.append(
                {
                    "url": canonical_url,
                    "handle": handle,
                    "author_name": result.get("name") or handle,
                    "text": text,
                    "score": score_text(text),
                    "signal_tags": signal_tags(text),
                    "discover_backend": f"x-api:{resolved_backend}",
                    "fetch_backend": f"x-api:{resolved_backend}",
                    "published_date": published_date.isoformat() if published_date else None,
                    "fetched_at": fetched_at,
                }
            )

    for handle in handles:
        clean_handle = handle.lstrip("@")
        if clean_handle.lower() not in result_handles:
            failed_handles.append(clean_handle)

    unique_failed = []
    seen_failed = set()
    for handle in failed_handles:
        key = handle.lower()
        if key in seen_failed:
            continue
        seen_failed.add(key)
        unique_failed.append(handle)

    log(f"x-api kept {len(candidates)} signal candidate(s); failed_accounts={len(unique_failed)}")
    return candidates, unique_failed


def render_candidates_markdown(
    candidates: List[Dict[str, Any]],
    days: int,
    after: str,
    accounts_count: int,
) -> str:
    lines = [
        f"# Creator signal candidates (last {days} days)",
        f"- after: {after}",
        f"- accounts: {accounts_count}",
        f"- collected: {len(candidates)}",
        "",
    ]

    for index, candidate in enumerate(candidates[:60], 1):
        tags = ", ".join(candidate.get("signal_tags") or []) or "uncategorized"
        lines.append(f"## {index}. @{candidate['handle']} (score={candidate['score']} tags={tags})")
        lines.append(candidate["url"])
        lines.append("")
        meta_bits = [
            f"discovered_via={candidate['discover_backend']}",
            f"fetched_via={candidate['fetch_backend']}",
        ]
        if candidate.get("published_date"):
            meta_bits.append(f"published_date={candidate['published_date']}")
        lines.append("- " + " | ".join(meta_bits))
        lines.append("")
        lines.append(candidate["text"][:800].strip())
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--accounts", default=str(Path(__file__).resolve().parent.parent / "references/accounts.txt"))
    parser.add_argument("--seed-urls", default="", help="Optional file with known X status URLs, one per line.")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Handle batch size for opencli-google discovery.",
    )
    parser.add_argument("--per-search", type=int, default=20)
    parser.add_argument("--outdir", default=str(Path.cwd() / "output"))
    parser.add_argument(
        "--lang",
        default="en",
        help="Language passed to opencli-google discovery.",
    )
    parser.add_argument(
        "--keywords-config",
        default="",
        help="Optional JSON file with kw/exclude_hints/weak_negative_hints/signal_hints to override built-in defaults.",
    )
    parser.add_argument(
        "--discover-backend",
        choices=("x-api", "auto", "syndication", "opencli", "opencli-google", "opencli-twitter", "none"),
        default="x-api",
        help=(
            "Discovery backend. x-api uses the local fetch_x_posts X API backend;"
            "auto keeps the legacy opencli/syndication discovery chain."
        ),
    )
    parser.add_argument(
        "--x-api-backend",
        choices=("auto", "getxapi", "twitterapiio", "official"),
        default="auto",
        help=(
            "X API backend for --discover-backend x-api. auto uses "
            "GETX_API_KEY, then TWITTERAPI_IO_KEY, then X_BEARER_TOKEN."
        ),
    )
    parser.add_argument(
        "--x-api-fallback-backend",
        choices=("none", "auto", "syndication", "opencli", "opencli-google", "opencli-twitter"),
        default="opencli-twitter",
        help=(
            "Fallback discovery backend for accounts whose x-api fetch fails. "
            "Default is opencli-twitter."
        ),
    )
    parser.add_argument(
        "--fetch-backend",
        choices=("auto", "oembed"),
        default="auto",
    )
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument(
        "--allow-low-signal",
        action="store_true",
        help="Keep posts even when they do not match signal keyword heuristics.",
    )
    args = parser.parse_args()

    accounts_path = Path(args.accounts).expanduser().resolve()
    if not accounts_path.exists():
        print(f"accounts file not found: {accounts_path}", file=sys.stderr)
        sys.exit(1)

    handles = load_handles(accounts_path)
    today = dt.date.today()
    cutoff_date = today - dt.timedelta(days=args.days)
    after = cutoff_date.isoformat()

    outdir = Path(args.outdir).expanduser().resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    if args.keywords_config:
        config_path = Path(args.keywords_config).expanduser().resolve()
        if not config_path.exists():
            log(f"warn: keywords-config file not found: {config_path}, using built-in defaults")
        else:
            cfg = load_keywords_config(str(config_path))
            if cfg.get("kw") is not None:
                KW[:] = cfg["kw"]
            if cfg.get("exclude_hints") is not None:
                EXCLUDE_HINTS[:] = cfg["exclude_hints"]
            if cfg.get("weak_negative_hints") is not None:
                WEAK_NEGATIVE_HINTS[:] = cfg["weak_negative_hints"]
            if cfg.get("signal_hints") is not None:
                SIGNAL_HINTS.clear()
                SIGNAL_HINTS.update(cfg["signal_hints"])
            global KW_HINT_RE
            KW_HINT_RE = keyword_hint_regex()
            log(f"loaded keywords-config: {config_path}")

    log(
        f"starting scan: accounts={len(handles)} days={args.days} "
        f"discover={args.discover_backend} fetch={args.fetch_backend} outdir={outdir}"
    )

    candidates: List[Dict[str, Any]] = []
    discovered_urls: Dict[str, str]
    if args.seed_urls:
        seed_path = Path(args.seed_urls).expanduser().resolve()
        if not seed_path.exists():
            print(f"seed urls file not found: {seed_path}", file=sys.stderr)
            sys.exit(1)
        discovered_urls = load_seed_urls(seed_path)
        log(f"loaded {len(discovered_urls)} seed urls from {seed_path}")
    elif args.discover_backend == "x-api":
        fallback_handles: List[str] = []
        try:
            candidates, fallback_handles = fetch_candidates_x_api(
                handles=handles,
                days=args.days,
                cutoff_date=cutoff_date,
                x_api_backend=args.x_api_backend,
                require_signal=not args.allow_low_signal,
            )
        except ConfigurationError as exc:
            if args.x_api_fallback_backend == "none":
                print(f"configuration error: {exc}", file=sys.stderr)
                sys.exit(2)
            log(f"warn: {exc}; falling back for all accounts")
            fallback_handles = handles[:]

        if fallback_handles and args.x_api_fallback_backend != "none":
            log(
                f"x-api fallback: {len(fallback_handles)} account(s) via "
                f"{args.x_api_fallback_backend}"
            )
            try:
                discovered_urls = discover_status_urls(
                    backend=args.x_api_fallback_backend,
                    handles=fallback_handles,
                    after=after,
                    cutoff_date=cutoff_date,
                    batch_size=args.batch_size,
                    per_search=args.per_search,
                    lang=args.lang,
                    timeout=args.timeout,
                    require_signal=not args.allow_low_signal,
                )
            except ConfigurationError as exc:
                log(f"warn: fallback backend failed: {exc}")
                discovered_urls = {}
        elif fallback_handles:
            log(f"x-api fallback disabled; skipped {len(fallback_handles)} failed account(s)")
            discovered_urls = {}
        else:
            discovered_urls = {}
    elif args.discover_backend == "none":
        print("discover-backend=none requires --seed-urls", file=sys.stderr)
        sys.exit(1)
    else:
        try:
            discovered_urls = discover_status_urls(
                backend=args.discover_backend,
                handles=handles,
                after=after,
                cutoff_date=cutoff_date,
                batch_size=args.batch_size,
                per_search=args.per_search,
                lang=args.lang,
                timeout=args.timeout,
                require_signal=not args.allow_low_signal,
            )
        except ConfigurationError as exc:
            print(f"configuration error: {exc}", file=sys.stderr)
            sys.exit(2)

    if discovered_urls:
        unique_urls = list(discovered_urls.keys())
        log(f"deduped candidate urls: {len(unique_urls)}")

        for index, status_url in enumerate(unique_urls, 1):
            try:
                info = fetch_tweet_info(status_url, backend=args.fetch_backend, timeout=args.timeout)
            except Exception as exc:  # pragma: no cover - runtime/network variability
                log(f"warn: fetch failed {status_url} {exc}")
                continue

            text = str(info.get("text") or "").strip()
            if not text:
                continue

            published_date = parse_dateish(str(info.get("published_date") or ""))
            if published_date and published_date < cutoff_date:
                continue

            match = STATUS_RE.search(status_url)
            handle = match.group(1) if match else ""
            canonical_url = normalize_status_url(str(info.get("canonical_url") or status_url)) or status_url
            candidate = {
                "url": canonical_url,
                "handle": handle,
                "author_name": info.get("author_name"),
                "text": text,
                "score": score_text(text),
                "signal_tags": signal_tags(text),
                "discover_backend": discovered_urls.get(status_url, "seed"),
                "fetch_backend": info.get("backend") or args.fetch_backend,
                "published_date": published_date.isoformat() if published_date else None,
                "fetched_at": dt.datetime.now().isoformat(timespec="seconds"),
            }
            candidates.append(candidate)

            if index % 10 == 0 or index == len(unique_urls):
                log(f"fetched {index}/{len(unique_urls)} urls, kept {len(candidates)} candidates")

    seen_candidate_urls = set()
    deduped_candidates: List[Dict[str, Any]] = []
    for candidate in candidates:
        url = str(candidate.get("url") or "")
        if not url or url in seen_candidate_urls:
            continue
        seen_candidate_urls.add(url)
        deduped_candidates.append(candidate)
    if len(deduped_candidates) != len(candidates):
        log(f"deduped candidates: {len(candidates)} -> {len(deduped_candidates)}")
    candidates = deduped_candidates

    before_noise = len(candidates)
    candidates = [c for c in candidates if not is_noisy_candidate(c["text"])]
    removed = before_noise - len(candidates)
    if removed:
        log(f"noise filter removed {removed} low-quality candidate(s) (kept {len(candidates)})")

    candidates.sort(key=lambda item: item.get("score", 0), reverse=True)

    (outdir / "candidates.json").write_text(json.dumps(candidates, ensure_ascii=False, indent=2) + "\n", "utf-8")
    (outdir / "candidates.md").write_text(
        render_candidates_markdown(candidates, days=args.days, after=after, accounts_count=len(handles)),
        "utf-8",
    )

    print(str(outdir / "candidates.json"))


if __name__ == "__main__":
    main()
