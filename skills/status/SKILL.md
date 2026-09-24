---
description: Wiki health at a glance — contract validity (via lint), page counts by type, unresolved [CONTESTED] and stale-synthesis counts, queue depths, and recent activity. Read-only; reports, never edits.
---

# /callosum:status

**When to use:** A quick health check of the mind wiki. For a prioritized fix queue, use `/callosum:prune`; status only reports.

## Process

1. **Run lint**: `python3 "$CALLOSUM_PLUGIN_ROOT/scripts/lint.py" "$CALLOSUM_MIND_ROOT" --format json` — report error/warning/info counts and the top kinds.
2. **Count pages** by `type` from `index.md` (entities, concepts, research, synthesis, ideas by verdict, collections).
3. **Count trust signals**: unresolved `[CONTESTED]` claims, `stale_synthesis` and `stale_verdict` findings (from the lint output — don't recompute).
4. **Queue depths**: files waiting in `raw/inbox/`, `raw/sources/`, `raw/ideas/`, `raw/questions/`, `raw/references/`, `raw/inconclusive/`; library items not yet distilled (`library_orphan` count).
5. **Recent activity**: last 10 lines of `log.md`, and `git -C "$CALLOSUM_MIND_ROOT" log --oneline -5` if it's a git repo.
6. **Report** in one compact block:

```
=== Mind Status ===
Contract : N errors, N warnings (top: <kind> xN, ...)
Pages    : N entities | N concepts | N research | N synthesis | N ideas (R/C/J) | N collection
Trust    : N [CONTESTED] unresolved | N stale syntheses | N stale verdicts
Queues   : inbox N | sources N | ideas N | questions N | references N | inconclusive N
Library  : N items, N not yet distilled
Recent   : <last log lines / commits>
```

## Rules

<HardGate>
1. Status is read-only. Never modify any file, never run lint with `--fix`.
</HardGate>
