#!/usr/bin/env python3
"""Install Callosum as a linked OpenClaw plugin.

    python3 setup_openclaw.py

This installer deliberately changes no model, provider, workspace, or hook settings. Callosum's
OpenClaw manifest declares its skills; host-level writes outside that manifest belong to the
user's OpenClaw configuration, not to this project.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(REPO, "openclaw.plugin.json")


def install(run=subprocess.run, which=shutil.which):
    if not os.path.isfile(MANIFEST):
        print(f"error: missing plugin manifest: {MANIFEST}", file=sys.stderr)
        return 1
    try:
        with open(MANIFEST, encoding="utf-8") as f:
            manifest = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: invalid plugin manifest: {exc}", file=sys.stderr)
        return 1

    missing = [rel for rel in manifest.get("skills", [])
               if not os.path.isfile(os.path.join(REPO, rel, "SKILL.md"))]
    if missing:
        print("error: manifest references missing skill directories: " + ", ".join(missing),
              file=sys.stderr)
        return 1
    if which("openclaw") is None:
        print("error: `openclaw` is not on PATH. Install or activate OpenClaw first.",
              file=sys.stderr)
        return 1

    result = run(["openclaw", "plugins", "install", "-l", REPO],
                 capture_output=True, text=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        print(f"error: OpenClaw plugin install failed: {detail}", file=sys.stderr)
        return result.returncode or 1

    print("Callosum installed as a linked OpenClaw plugin.")
    print("Restart the OpenClaw gateway, then verify that the Callosum skills are listed.")
    return 0


def main():
    return install()


if __name__ == "__main__":
    sys.exit(main())
