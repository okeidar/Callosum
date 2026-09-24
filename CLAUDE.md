# Callosum - Knowledge Wiki Skills

This is Callosum, a personal knowledge system that operates on a mind wiki (default `~/mind/`).

## Skills

- `/callosum:classify` - classify inbox files to processing queues
- `/callosum:absorb` - process sources into wiki (sole page author; captures sources into library/)
- `/callosum:catalog` - file references into wiki collections
- `/callosum:recall` - query and synthesize from wiki (synthesis cache → pages → library)
- `/callosum:incubate` - develop raw ideas into verdicts (RIPENED/REJECTED/CONDITIONAL)
- `/callosum:investigate` - research open questions into research pages
- `/callosum:prune` - health scanner (folds in lint; read-only)
- `/callosum:adapt` - fix resolver (human-gated)
- `/callosum:status` - health snapshot (read-only)

Skills are in `skills/`. The `mind` agent (`agents/mind.md`) is the gateway other projects use.

## Data vs knowledge

The contract governs the **knowledge machinery only** — the reserved folders `wiki/entities/`,
`wiki/concepts/`, `wiki/research/`, `wiki/synthesis/`, `wiki/ideas/` (Compiled Truth + Timeline,
`^tN` anchors, per-claim citations). **Everything else under `wiki/` is arbitrary data**: domain
folders coined on demand from the content hold free-form pages — no citations, no required
frontmatter, no `^tN`. The page looks like whatever it is. This is what lets Callosum hold any
topic without being told in advance what it is; the domain type is never hardcoded anywhere in
the core.

## Plugins

Plugins are apps with a UI whose read-only data layer is the derived wiki pages. They read
`wiki/`, never `library/` or `raw/`, and never write. `examples/` holds sample plugins (a
board over the idea pipeline, and a data-collection browser) — the domain-specific ones are
illustrations, not part of the core.

## Deterministic layer

- `template/wiki-contract.md` — the machine-checkable contract (single source of truth: `scripts/checks.py`)
- `hooks/hooks.json` — the ONLY hook wiring authority: prewrite gate (blocks contract violations, fails closed), postwrite bookkeeping (stamps last-updated, index.md, log.md, link normalization), session env
- `python3 -m scripts.lint <mind-root> [--fix] [--format json]` — tree-wide validation; `--fix` regenerates index.md
- `scripts/land_run.py` — one local git commit per processed source (no PRs, no CI — personal system)

Rule: a job is a script only if it is deterministic; anything needing judgment is a skill.
Skills never do bookkeeping (index/log/last-updated) — hooks own it.
