---
description: Resolves issues found by /callosum:prune. Human-gated — presents fix proposals one at a time, applies only with approval. Routes fixes needing new facts to /callosum:absorb; lands approved fixes as commits.
argument-hint: [issue-id]
---

# /callosum:adapt

**When to use:** You have `/callosum:prune` output and want to resolve the issues it found.

## Arguments

- **No argument** — read prune output from the current conversation and begin the fix loop.
- **Issue ID** — jump directly to a specific issue from a prior prune report.

## The one decision

For each issue ask: **does the fix need a fact that is not already in the wiki?**

- **No** → repair in place: repoint a citation, fix a link, make links bidirectional, merge duplicate pages, re-derive a stale synthesis from its `derived_from` pages, run `python3 "$CALLOSUM_PLUGIN_ROOT/scripts/lint.py" "$CALLOSUM_MIND_ROOT" --fix` for generated-artifact drift.
- **Yes** → route to absorb: write a short note describing what's needed into `raw/sources/` (or `raw/questions/` if it needs research first) and tell the user. Adapt never authors facts.
- **It's a truth call** (an unresolved `[CONTESTED]`, contradicting pages) → present both sides and ask the human to pick or reformulate. Never elect a winner yourself.

## Process

1. **Get prune output** — read from the current conversation, or run `/callosum:prune` fresh if none is present.
2. **Order issues** — work red → yellow → blue → green (highest severity first).
3. **For each issue:**
   - Analyze and decide via The one decision above.
   - Present one proposal at a time (see Proposal Format below).
   - Wait for human approval.
   - On approval: apply the fix. If the fix touches an existing `type: idea` page, run the edit with `CALLOSUM_ALLOW_IDEA_WRITE=1` — approval is what sanctions it.
   - On skip: note it and move to the next issue.
4. **Land** approved fixes when done:
   `python3 "$CALLOSUM_PLUGIN_ROOT/scripts/land_run.py" --actor adapt --source <issue-id> <files edited>`
   Each landing is one commit — that is the rollback unit if a fix turns out wrong.

## Proposal Format

```
=== Issue: <id> <type> ===
Page: [[Page Name]]
Problem: <description>
Fix: <what will be done>  (in-place | route-to-absorb | human-decision)
Risk: low | medium | high
Reversibility: easy | hard

Approve? (yes / skip)
```

## Rules

<HardGate>
1. Never apply a fix without explicit human approval. No exceptions.
2. Never batch multiple fixes into one approval step — one proposal at a time, always.
3. Never author new facts — a fix that needs a fact not in the wiki routes to absorb.
</HardGate>

4. `log.md`, `index.md`, and `last-updated` are maintained by hooks — never edit them directly (`lint --fix` is the sanctioned repair for index drift).
