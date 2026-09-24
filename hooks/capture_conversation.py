#!/usr/bin/env python3
"""SessionEnd/PreCompact hook: park the conversation transcript into the mind's inbox.

Deliberately scoped for a personal system — this fires for every Claude Code session once
the plugin is installed at user scope, so it captures ONLY when the session ran inside a
mind root (cwd has a .callosum ancestor), or when CALLOSUM_CAPTURE=1 forces capture into the
default mind. CALLOSUM_CAPTURE_OFF=1 disables it entirely. Idempotent per session.

The parked transcript is an ordinary inbox item: /classify routes it, /absorb distills it.
Nothing writes wiki pages silently.
"""
import json
import os
import shutil
import sys
from datetime import datetime

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PLUGIN_ROOT)

from scripts import mind_utils as mu  # noqa: E402

MIN_BYTES = 2048  # ignore trivially short sessions


def main():
    if os.environ.get("CALLOSUM_CAPTURE_OFF") == "1":
        return
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    transcript = data.get("transcript_path", "")
    if not transcript or not os.path.exists(transcript):
        return
    if os.path.getsize(transcript) < MIN_BYTES:
        return

    cwd = data.get("cwd") or os.getcwd()
    root = mu.find_mind_root(cwd)
    if not root and os.environ.get("CALLOSUM_CAPTURE") == "1":
        root = mu.resolve_default_mind_root()
    if not root:
        return

    session = (data.get("session_id") or "session")[:8]
    inbox = os.path.join(root, "raw", "inbox")
    os.makedirs(inbox, exist_ok=True)
    target = os.path.join(
        inbox, f"conversation-{datetime.now():%Y%m%d}-{session}.jsonl")
    if os.path.exists(target):
        return  # already parked (SessionEnd + PreCompact can both fire)
    try:
        shutil.copy2(transcript, target)
    except OSError as exc:
        print(f"callosum capture: {exc!r}", file=sys.stderr)


if __name__ == "__main__":
    main()
