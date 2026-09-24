#!/usr/bin/env python3
"""SessionStart hook: resolve the mind root and export env for skills and scripts.

Writes CALLOSUM_MIND_ROOT and CALLOSUM_PLUGIN_ROOT into $CLAUDE_ENV_FILE so that skills can
call the plugin's scripts (land_run, lint) from Bash without hardcoded paths.
Resolution order: $CALLOSUM_MIND_ROOT → nearest .callosum ancestor of cwd → ~/mind.
"""
import os
import sys

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PLUGIN_ROOT)

from scripts import mind_utils as mu  # noqa: E402


def main():
    env_file = os.environ.get("CLAUDE_ENV_FILE")
    if not env_file:
        return
    root = mu.resolve_default_mind_root()
    try:
        with open(env_file, "a", encoding="utf-8") as f:
            if root:
                f.write(f'export CALLOSUM_MIND_ROOT="{root}"\n')
            f.write(f'export CALLOSUM_PLUGIN_ROOT="{PLUGIN_ROOT}"\n')
    except OSError as exc:
        print(f"callosum session_env: {exc!r}", file=sys.stderr)


if __name__ == "__main__":
    main()
