#!/usr/bin/env python3
"""Install Callosum for Claude Code.

    python3 setup_claudecode.py [target]            deploy a fresh mind (default ~/mind) + install plugin
    python3 setup_claudecode.py --refresh [target]  re-sync infra files into an existing mind
    python3 setup_claudecode.py --no-plugin [target]  skip the plugin step

Hooks are declared ONCE, in hooks/hooks.json, and travel with the plugin. Setup never writes
hook config into settings.json — if a previous install left the legacy pre_run/post_run hooks
there, setup removes them.

`--refresh` closes the template↔live drift loop: infra files the template owns (AGENTS.md,
wiki-contract.md, wiki/ideas/AGENTS.md) are re-copied into the deployed mind; content
(wiki/, library/, raw/, archive/, index, log) is never touched. Improve the template, then
refresh your mind.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(REPO, "template")

# files the template owns inside a deployed mind — safe to overwrite on --refresh
INFRA_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    "wiki-contract.md",
    "wiki/ideas/AGENTS.md",
    ".gitignore",
]


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def install_plugin():
    """Install the plugin and return whether both required commands succeeded."""
    print("Registering Callosum marketplace...")
    r = run(["claude", "plugin", "marketplace", "add", "--scope", "user", REPO])
    if r.returncode != 0:
        print(f"  error: marketplace add failed: {r.stderr.strip()}", file=sys.stderr)
        return False
    print("Installing Callosum plugin (user scope)...")
    r = run(["claude", "plugin", "install", "--scope", "user", "callosum"])
    if r.returncode != 0:
        print(f"  error: plugin install failed: {r.stderr.strip()}", file=sys.stderr)
        return False
    print("  plugin installed — hooks and skills come from the plugin itself.")
    return True


def remove_legacy_hooks():
    """Strip the pre_run/post_run hook wiring older setups wrote into settings.json."""
    for settings_path in (
        os.path.join(REPO, ".claude", "settings.json"),
        os.path.expanduser("~/.claude/settings.json"),
    ):
        if not os.path.exists(settings_path):
            continue
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
        except Exception:
            continue
        hooks = settings.get("hooks") or {}
        changed = False
        for event in list(hooks):
            kept = []
            for entry in hooks[event]:
                cmds = json.dumps(entry)
                if "pre_run.py" in cmds or "post_run.py" in cmds or "post_tool_use.py" in cmds:
                    changed = True
                    continue
                kept.append(entry)
            if kept:
                hooks[event] = kept
            else:
                del hooks[event]
                changed = True
        if changed:
            settings["hooks"] = hooks
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)
            print(f"  removed legacy hook wiring from {settings_path}")


def deploy(target):
    """Deploy a fresh mind without merging into an unrelated existing directory."""
    if os.path.exists(os.path.join(target, ".callosum")):
        print(f"Mind already exists at {target} — use --refresh to re-sync infra files.")
        return False
    if os.path.lexists(target):
        if os.path.islink(target) or not os.path.isdir(target) or os.listdir(target):
            print(f"Refusing to deploy over non-empty or unsafe target: {target}", file=sys.stderr)
            return False
    print(f"Deploying mind template to {target} ...")
    shutil.copytree(TEMPLATE, target, dirs_exist_ok=True)
    if not os.path.isdir(os.path.join(target, ".git")):
        for cmd in (["git", "-C", target, "init"],
                    ["git", "-C", target, "add", "-A"],
                    ["git", "-C", target, "-c", "user.name=Callosum",
                     "-c", "user.email=callosum@local", "commit", "-m",
                     "Initialize mind wiki from Callosum template"]):
            r = run(cmd)
            if r.returncode != 0:
                print(f"error: {' '.join(cmd)} failed: {r.stderr.strip()}", file=sys.stderr)
                return False
        print("  git initialized with an initial commit.")
    print("  deployed.")
    return True


def refresh(target):
    if not os.path.exists(os.path.join(target, ".callosum")):
        print(f"error: {target} is not a mind root (no .callosum marker)", file=sys.stderr)
        sys.exit(1)
    print(f"Refreshing infra files in {target} (content untouched) ...")
    for rel in INFRA_FILES:
        src = os.path.join(TEMPLATE, rel)
        if not os.path.exists(src):
            continue
        dst = os.path.join(target, rel)
        parent = os.path.dirname(dst)
        # Infra refresh is allowed to replace owned files, never to traverse a
        # user-created symlink and write outside the mind.
        cursor = target
        unsafe = os.path.islink(target)
        for part in os.path.relpath(parent, target).split(os.sep):
            if part == ".":
                continue
            cursor = os.path.join(cursor, part)
            if os.path.islink(cursor):
                unsafe = True
                break
        if unsafe or os.path.islink(dst):
            print(f"error: refusing to refresh through symlink: {dst}", file=sys.stderr)
            return False
        os.makedirs(parent, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"  synced {rel}")
    os.makedirs(os.path.join(target, "library"), exist_ok=True)
    print("  done. Review with: git -C <mind> diff")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("target", nargs="?", default=os.path.expanduser("~/mind"))
    ap.add_argument("--refresh", action="store_true", help="re-sync infra files into an existing mind")
    ap.add_argument("--no-plugin", action="store_true", help="skip plugin installation")
    args = ap.parse_args()

    target = os.path.abspath(os.path.expanduser(args.target))
    if args.refresh:
        deploy_ok = refresh(target)
    else:
        deploy_ok = deploy(target)
    plugin_ok = args.no_plugin or install_plugin()
    remove_legacy_hooks()

    print("\n=== Verification ===")
    print(f"  mind root      : {'OK' if os.path.exists(os.path.join(target, '.callosum')) else 'MISSING'} ({target})")
    print(f"  wiki contract  : {'OK' if os.path.exists(os.path.join(target, 'wiki-contract.md')) else 'MISSING'}")
    print(f"  plugin hooks   : {'OK' if os.path.exists(os.path.join(REPO, 'hooks', 'hooks.json')) else 'MISSING'} (declared in hooks/hooks.json only)")
    print("  plugin install : " + ("SKIPPED" if args.no_plugin else ("OK" if plugin_ok else "FAILED")))
    print("  try            : claude, then /callosum:classify or /callosum:absorb inside the mind, or `python3 -m scripts.lint " + target + "`")
    if not deploy_ok or not plugin_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
