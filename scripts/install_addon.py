#!/usr/bin/env python3
"""One-command installer for Callosum addons (the plugins under examples/).

Addons are apps over the mind wiki's derived pages. Two shapes (see examples/README.md):
a UI (`serve.py`) and/or an agent-side skill (`SKILL.md`). This installer is generic — it
inspects what a directory ships; it knows nothing about any addon's domain.

    python3 -m scripts.install_addon --list
    python3 -m scripts.install_addon <addon-name> [--skills-dir ~/.claude/skills] [--force] [--dry-run]

Installing a skill addon copies its directory into the skills dir (default
~/.claude/skills). A UI addon is not copied — it runs from the repo; the installer prints
the exact command. Exit codes: 0 ok, 1 error, 2 bad invocation.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES = os.path.join(REPO, "examples")


def discover(examples_dir=EXAMPLES):
    """Map addon name -> {'skill': bool, 'ui': bool, 'path': dir}. An addon is any
    directory shipping a SKILL.md and/or a serve.py."""
    addons = {}
    if not os.path.isdir(examples_dir):
        return addons
    for name in sorted(os.listdir(examples_dir)):
        d = os.path.join(examples_dir, name)
        if not os.path.isdir(d):
            continue
        skill = os.path.exists(os.path.join(d, "SKILL.md"))
        ui = os.path.exists(os.path.join(d, "serve.py"))
        if skill or ui:
            metadata = {}
            manifest = os.path.join(d, "addon.json")
            if os.path.exists(manifest):
                try:
                    import json
                    with open(manifest, "r", encoding="utf-8") as f:
                        metadata = json.load(f)
                except (OSError, ValueError):
                    metadata = {}
            addons[name] = {"skill": skill, "ui": ui, "path": d,
                            "requires_executables": metadata.get("requires_executables") or [],
                            "prerequisite_note": metadata.get("prerequisite_note", "")}
    return addons


def install(name, skills_dir, examples_dir=EXAMPLES, force=False, dry_run=False, out=print):
    addons = discover(examples_dir)
    if name not in addons:
        known = ", ".join(sorted(addons)) or "none found"
        print(f"unknown addon {name!r} — available: {known}", file=sys.stderr)
        return 1
    addon = addons[name]
    missing = [exe for exe in addon["requires_executables"] if shutil.which(exe) is None]
    if missing:
        print(f"cannot prepare addon {name!r}: missing executable(s): {', '.join(missing)}",
              file=sys.stderr)
        if addon["prerequisite_note"]:
            print(addon["prerequisite_note"], file=sys.stderr)
        return 1
    if addon["skill"]:
        if os.path.lexists(skills_dir) and (os.path.islink(skills_dir) or not os.path.isdir(skills_dir)):
            print(f"unsafe skills directory: {skills_dir}", file=sys.stderr)
            return 1
        dest = os.path.join(skills_dir, name)
        if os.path.lexists(dest) and (os.path.islink(dest) or not os.path.isdir(dest)):
            print(f"unsafe addon destination: {dest}", file=sys.stderr)
            return 1
        if os.path.exists(dest) and not force:
            print(f"{dest} already exists — pass --force to overwrite", file=sys.stderr)
            return 1
        if dry_run:
            out(f"would install skill {name} -> {dest}")
        else:
            if os.path.exists(dest):
                shutil.rmtree(dest)
            os.makedirs(skills_dir, exist_ok=True)
            real_skills = os.path.realpath(skills_dir)
            if os.path.commonpath((os.path.realpath(dest), real_skills)) != real_skills:
                print(f"addon destination escapes skills directory: {dest}", file=sys.stderr)
                return 1
            shutil.copytree(addon["path"], dest)
            out(f"installed skill {name} -> {dest}")
            out(f"  use it as /{name} in Claude Code")
    if addon["ui"]:
        serve = os.path.join(addon["path"], "serve.py")
        if not addon["skill"]:
            out(f"UI-only addon {name}: no files are installed; it runs from this clone.")
        else:
            out(f"UI included with addon {name}; run it from this clone.")
        out(f"  python3 {serve} \"$CALLOSUM_MIND_ROOT\"")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("addon", nargs="?", help="addon directory name under examples/")
    ap.add_argument("--list", action="store_true", help="list available addons")
    ap.add_argument("--skills-dir", default=os.path.expanduser("~/.claude/skills"))
    ap.add_argument("--force", action="store_true", help="overwrite an existing installed skill")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    if args.list:
        addons = discover()
        for name, a in addons.items():
            kinds = "+".join(k for k in ("skill", "ui") if a[k])
            print(f"{name:24} [{kinds}] {a['path']}")
        return 0
    if not args.addon:
        ap.print_help()
        return 2
    return install(args.addon, os.path.abspath(os.path.expanduser(args.skills_dir)),
                   force=args.force, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
