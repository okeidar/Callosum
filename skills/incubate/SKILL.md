---
description: Develops raw ideas into actionable verdicts (RIPENED, REJECTED, CONDITIONAL). Researches internally and externally, evaluates against principles, publishes to wiki/ideas/.
argument-hint: <idea-name | path>
---

# /callosum:incubate

**When to use:** You have a specific idea in `raw/ideas/` that you want to develop and evaluate.

## Arguments

- **Idea name or path** (required) — the idea file to incubate. Matches by filename in `raw/ideas/` if a bare name is given, or reads directly if a full path is provided.
- If no argument is given, list the available ideas in `raw/ideas/` and ask the user which one to process.

## Process

1. **Read** the idea file fully — ideas can be long and detailed; the full content is the input.
2. **Pattern scan** — scan the entire `wiki/ideas/` folder (including `rejected/`, `conditional/`, and ripened idea subdirectories) for similar past ideas. You need to know if a similar idea was already ripened (don't duplicate), previously rejected (understand why), or is still conditional (may be the same blocker).
4. **Internal research** — search `index.md` and read relevant wiki pages for related concepts, entities, and principles.
5. **External research** — use web search to check if the idea already exists, is solved, or has known pitfalls. If web search is unavailable, proceed on internal research only and note the limitation in the verdict.
6. **Capture knowledge** — if research surfaces generally useful facts worth keeping in the wiki, invoke `/callosum:investigate` with the relevant question or topic. Let investigate handle synthesis and writing.
7. **Evaluate against principles** — check any wiki pages with `type: principle` that apply to this idea.
8. **Render verdict**:
   - **RIPENED** — valid, novel, and actionable.
   - **REJECTED** — flawed, already solved, or violates a principle.
   - **CONDITIONAL** — promising but blocked by specific unresolved conditions.
9. **Publish** the enriched idea document to the appropriate folder:
   - RIPENED → `wiki/ideas/[idea-name]/[idea-name].md` (each ripened idea gets its own subdirectory)
   - REJECTED → `wiki/ideas/rejected/[idea-name].md`
   - CONDITIONAL → `wiki/ideas/conditional/[idea-name].md`

   The published document is the **original idea file content preserved in full**, with the verdict appended as a clearly-delimited section at the end. Do not replace or compress the original content — it is the primary value of the document. For ripened ideas especially, the full content is what gets used as a project seed or recalled for synthesis.

   Re-incubating an idea that already has a published page is the one sanctioned modification of an existing idea page: run that write with `CALLOSUM_ALLOW_IDEA_WRITE=1` (the gate blocks unilateral idea edits otherwise).
10. **Archive** the original idea file to `archive/ideas/`.
11. **Land** — `python3 "$CALLOSUM_PLUGIN_ROOT/scripts/land_run.py" --actor incubate --source <idea-name> <files>`

## Verdict Format

The published document is the original idea content with its frontmatter augmented and a verdict section appended. The original content is never summarized or replaced.

```markdown
---
title: [Idea Name]
type: idea
verdict: RIPENED | REJECTED | CONDITIONAL
date: YYYY-MM-DD
domain: [domain]
tags: [tag1, tag2]
related-pages: ["[[Page Name]]"]
synthesized: true
---

[FULL ORIGINAL IDEA CONTENT — preserved exactly as written]

---

## Verdict: RIPENED | REJECTED | CONDITIONAL

**Date:** YYYY-MM-DD
**Complexity:** Low | Medium | High
**Principle alignment:** [brief note on how it fits or conflicts with personal principles]

### Reasoning
[Why this verdict was reached — the core argument]

### Key Findings
[What research surfaced that wasn't in the original idea — new information, prior art, known pitfalls, market context]

### Basis
- [[Page Name]] (last-updated: YYYY-MM-DD)
- [[Another Page]] (last-updated: YYYY-MM-DD)

### Conditions
[If CONDITIONAL: specific blockers that must be resolved before proceeding. Each blocker is a concrete decision or fact, not a vague concern.]
```

## Rules

<HardGate>
1. Never render a verdict without completing both internal and external research (or explicitly noting that external was unavailable).
2. Always use specific, disambiguated filenames for any new concept pages created during research (e.g., `graph_db_traversal_performance.md`, not `performance.md`).
3. Always archive the original idea file after the verdict is published.
4. Always include a `## Basis` section listing every wiki page referenced during research, with each page's `last-updated` date recorded at the time the verdict was rendered. This enables `/callosum:prune` and `lint` to detect stale verdicts when basis pages are updated.
</HardGate>

5. Do NOT author `last-updated` or touch `index.md`/`log.md` — hooks own bookkeeping.
