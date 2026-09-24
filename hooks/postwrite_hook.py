#!/usr/bin/env python3
"""PostToolUse bookkeeping for Callosum. Fires after Write/Edit/MultiEdit inside a mind root.

Deterministic side effects the skills must never do themselves:
- stamp `last-updated` in wiki-page frontmatter (inserted if absent)
- normalize path-form inline links to [[slug]] form in wiki-page bodies
- upsert the page's line in index.md
- append a line to log.md (wiki writes and library captures)

Best-effort by design: bookkeeping failures must never block the session, so all errors are
swallowed after a stderr note. Validation already happened in the prewrite gate.
"""
import json
import os
import re
import sys
from datetime import datetime

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PLUGIN_ROOT)

from scripts import mind_utils as mu  # noqa: E402

WRITE_TOOLS = {"Write", "Edit", "MultiEdit"}


def normalize_inline_links(body: str) -> str:
    def repl(m):
        path, display = m.group(1), m.group(2) or ""
        slug = os.path.splitext(os.path.basename(path))[0]
        return f"[[{slug}{display}]]"
    return mu.INLINE_PATH_LINK_RE.sub(repl, body)


def stamp_last_updated(fm_text: str, stamp: str) -> str:
    if re.search(r"^last-updated:.*$", fm_text, re.MULTILINE):
        return re.sub(r"^last-updated:.*$", f"last-updated: {stamp}", fm_text, flags=re.MULTILINE)
    return fm_text.rstrip("\n") + f"\nlast-updated: {stamp}\n"


def extract_description(body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped[:120]
    return ""


def upsert_index(index_path, title, rel_path, page_type, domain, description):
    entry = f"- [{title}]({rel_path}) | {page_type} | {domain} | {description}\n"
    lines = []
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    for i, line in enumerate(lines):
        if f"]({rel_path})" in line and line.strip().startswith("-"):
            lines[i] = entry
            with open(index_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            return False
    with open(index_path, "a", encoding="utf-8") as f:
        f.write(entry)
    return True


def append_log(log_path, message):
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(message + "\n")


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    if data.get("tool_name") not in WRITE_TOOLS:
        return
    file_path = (data.get("tool_input") or {}).get("file_path", "")
    if not file_path:
        return
    mind_root = mu.find_mind_root(file_path)
    if not mind_root or not os.path.exists(file_path):
        return

    rel = mu.relpath_in_root(file_path, mind_root)
    if rel in ("index.md", "log.md"):
        return
    index_path = os.path.join(mind_root, "index.md")
    log_path = os.path.join(mind_root, "log.md")
    now = datetime.now()

    try:
        if rel.startswith("library/"):
            append_log(log_path, f"{now:%Y-%m-%d %H:%M} — captured: {rel}")
            return
        if not rel.startswith("wiki/") or not rel.endswith(".md"):
            return

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        fm_text, body = mu.split_frontmatter(content)
        if fm_text is None:
            return

        new_fm = stamp_last_updated(fm_text, f"{now:%Y-%m-%d}")
        new_body = normalize_inline_links(body)
        if new_fm != fm_text or new_body != body:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"---\n{new_fm.strip()}\n---\n{new_body}")

        fm, _ = mu.parse_frontmatter(content)
        if not fm or "title" not in fm:
            return
        created = upsert_index(
            index_path, fm.get("title", ""), rel, fm.get("type", "unknown"),
            fm.get("domain", "unknown"), extract_description(new_body),
        )
        action = "created" if created else "updated"
        append_log(log_path, f"{now:%Y-%m-%d %H:%M} — {action}: [{fm.get('title','')}]({rel}) [{fm.get('domain','unknown')}]")
    except Exception as exc:  # noqa: BLE001
        print(f"callosum postwrite: non-fatal bookkeeping error: {exc!r}", file=sys.stderr)


if __name__ == "__main__":
    main()
