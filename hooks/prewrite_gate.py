#!/usr/bin/env python3
"""PreToolUse gate for Callosum: blocks writes that violate the wiki contract.

Reads the tool call as JSON on stdin. Exit 0 = allow, exit 2 = block (stderr is fed back to
the agent). Only writes inside a mind root (a .callosum ancestor) are checked; everything
else passes untouched. Once a write IS a mind write, the gate fails closed: an internal
error blocks the write rather than letting unvalidated content land.

Validation rules live in scripts/checks.py — the single source of truth shared with lint.
"""
import json
import os
import sys

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PLUGIN_ROOT)

from scripts import checks, mind_utils as mu  # noqa: E402

WRITE_TOOLS = {"Write", "Edit", "MultiEdit"}


def resulting_content(tool_name, tool_input, file_path):
    if tool_name == "Write":
        return tool_input.get("content", "")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        content = ""
    edits = tool_input.get("edits") if tool_name == "MultiEdit" else [tool_input]
    for edit in edits or []:
        old = edit.get("old_string", "")
        new = edit.get("new_string", "")
        if not old:
            content = new
        elif edit.get("replace_all"):
            content = content.replace(old, new)
        else:
            content = content.replace(old, new, 1)
    return content


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    if tool_name not in WRITE_TOOLS:
        sys.exit(0)
    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    if not file_path:
        sys.exit(0)

    mind_root = mu.find_mind_root(file_path)
    if not mind_root:
        sys.exit(0)  # not a mind write — none of our business

    # From here on: fail closed.
    try:
        content = resulting_content(tool_name, tool_input, file_path)
        issues = checks.check_write(mind_root, file_path, content, tool_name)
    except Exception as exc:  # noqa: BLE001
        print(
            f"Callosum gate error while validating {file_path}: {exc!r}. "
            "Failing closed — fix the gate environment before writing to the wiki.",
            file=sys.stderr,
        )
        sys.exit(2)

    blocks = [i for i in issues if i["severity"] == "block"]
    if blocks:
        lines = [f"Write blocked by the wiki contract ({len(blocks)} issue(s)):"]
        for b in blocks[:10]:
            lines.append(f"- [{b['kind']}] {b['message']}")
        lines.append("See wiki-contract.md at the mind root. Fix the content and retry.")
        print("\n".join(lines), file=sys.stderr)
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
