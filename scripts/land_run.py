#!/usr/bin/env python3
"""Deterministic landing: commit one processed source's writes as one local git commit.

Personal-wiki scope by design: local git only — no branches, no PRs, no CI. Called by a
skill as its final Persist step:

    python3 "$CALLOSUM_PLUGIN_ROOT/scripts/land_run.py" --actor absorb \
        --source <source-slug> [--root <mind-root>] <touched-file> [<touched-file> ...]

Rules (pinned):
- one commit per SOURCE, so each landing is independently revertable
- commit an EXPLICIT file list, never `git add -A` — unrelated dirty files must not be
  swept into a landing they don't belong to
- not a git repo / nothing staged → say so and exit 0 (landing is best-effort, never fatal)
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts import mind_utils as mu  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--actor", required=True, help="which skill is landing (absorb, catalog, ...)")
    ap.add_argument("--source", required=True, help="slug of the processed source")
    ap.add_argument("--root", default=None, help="mind root (default: resolved)")
    ap.add_argument("files", nargs="+", help="files touched by this source's processing")
    args = ap.parse_args()

    root = os.path.abspath(args.root) if args.root else mu.resolve_default_mind_root()
    if not root or not os.path.exists(os.path.join(root, ".callosum")):
        print("land_run: no mind root resolved — nothing landed", file=sys.stderr)
        return 0
    if not os.path.isdir(os.path.join(root, ".git")):
        print("land_run: mind root is not a git repository — nothing landed", file=sys.stderr)
        return 0

    rels = []
    for f in args.files:
        absf = os.path.abspath(f if os.path.isabs(f) else os.path.join(root, f))
        if not absf.startswith(root):
            print(f"land_run: skipping file outside mind root: {f}", file=sys.stderr)
            continue
        rels.append(os.path.relpath(absf, root))
    # index/log are always touched by the hooks alongside any page write
    for generated in ("index.md", "log.md"):
        if os.path.exists(os.path.join(root, generated)) and generated not in rels:
            rels.append(generated)
    if not rels:
        print("land_run: no files inside the mind root — nothing landed", file=sys.stderr)
        return 0

    def git(*argv):
        return subprocess.run(["git", "-C", root, *argv], capture_output=True, text=True)

    add = git("add", "--", *rels)
    if add.returncode != 0:
        print(f"land_run: git add failed: {add.stderr.strip()}", file=sys.stderr)
        return 1
    staged = git("diff", "--cached", "--name-only")
    if not staged.stdout.strip():
        print("land_run: nothing to commit for this source", file=sys.stderr)
        return 0
    msg = f"{args.actor}({args.source}): land {len([r for r in rels if r not in ('index.md', 'log.md')])} file(s)"
    # Commit only this landing's paths. The caller may already have unrelated changes
    # staged; plain `git commit` would silently sweep those into this source's commit even
    # though `git add` above used an explicit path list.
    commit = git("commit", "--only", "-m", msg, "--", *rels)
    if commit.returncode != 0:
        print(f"land_run: git commit failed: {commit.stderr.strip()}", file=sys.stderr)
        return 1
    print(f"landed: {msg}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
