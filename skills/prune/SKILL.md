---
description: Scans wiki pages for consistency issues. Runs the deterministic linter first, then adds judgment findings. Reports by severity: red (contradictions/stale verdicts/broken trust), yellow (orphans/duplicates/missing links), blue (schema/stale pages), green (opportunities).
argument-hint: [--full | --recent | --domain <name>]
---

# /callosum:prune

**When to use:** You want to check the wiki's health and surface issues for `/callosum:adapt` to fix.

## Arguments

- **No argument** — defaults to `--recent`
- `--full` — scan the entire wiki
- `--recent` — scan pages updated in the last 7 days
- `--domain <name>` — scan a specific domain only

## Process

1. **Run the linter first, scoped deterministically** — the deterministic layer owns contract checks:
   - `--full` → `python3 "$CALLOSUM_PLUGIN_ROOT/scripts/lint.py" "$CALLOSUM_MIND_ROOT" --format json`
   - `--recent` (default) → `python3 "$CALLOSUM_PLUGIN_ROOT/scripts/lint.py" "$CALLOSUM_MIND_ROOT" --format json --recent 7`
   - `--domain <name>` → full lint; you filter findings to the domain's pages
   Fold its findings into the report by kind (see mapping below). Do not re-derive by hand anything lint already computes (schema violations, unresolved citations/links, bidirectionality, index drift, `stale_synthesis`, `stale_verdict`, `library_orphan`). Scoped lint skips the tree-level checks (index drift, library orphans, secrets sweep) — those are full-pass only by nature.
2. **Determine scope** from the argument (default: `--recent`) — the page inventory comes from lint's `scope` line / `index.md`, never from reading `log.md` timestamps by hand.
3. **Read** `index.md` to get the page inventory for the scope.
4. **Scan** in-scope pages for the issues that need judgment — the things a script can't see:

### Red — Critical (broken trust)
- **Contradiction across pages**: two pages claim opposing things about the same subject.
- **Unresolved `[CONTESTED]`**: a Compiled Truth claim still carrying the marker — list it with both cited anchors so a human can resolve.
- From lint: `claim_uncited`, `citation_unresolved`, `source_path_unresolved`, `contested_single_cited`, `timeline_anchor_removed`, `stale_verdict`.

### Yellow — Warning (weak retrieval)
- **Cross-area duplication**: the same subject covered as parallel pages under different names or category folders (e.g. `entities/harnesses/claude-code` vs `entities/frameworks/claude`). Compare titles, slugs, and Compiled Truth summaries across folders — this is exactly what a slug match misses.
- **Orphan**: a page with 0 inbound links from other pages.
- **Missing WikiLink**: an entity mentioned in body text but not linked with `[[WikiLink]]`.
- From lint: `page_link_unresolved`, `related_pages_not_bidirectional`, `stale_synthesis`.

### Blue — Info (hygiene)
- **Stale page**: `last-updated` more than 6 months ago with no recent sources.
- From lint: `frontmatter_field_missing`, `missing_last_updated`, `index_drift`, `legacy_uncited`, `legacy_source_location`.

### Green — Opportunity
- **Accumulation**: 5+ pages in one domain with no synthesis page.
- From lint: `library_orphan` (a captured source not yet distilled — an absorb candidate).

5. **Report** all findings grouped by severity (see Report Format). Give each issue a stable id (`kind|page|evidence`) so `/callosum:adapt` can target it and repeat runs dedupe.
6. **Recommend** next step: run `/callosum:adapt` to resolve red and yellow issues.

## Report Format

```
=== Prune: <scope> | <N> issues ===

RED (N)
- [red-1] [[Page A]] contradicts [[Page B]]: <brief description>
- [red-2] Unresolved [CONTESTED] in [[Page]]: <claim>
- [red-3] Stale verdict: [[Idea Name]] (rendered: YYYY-MM-DD, [[Basis Page]] updated: YYYY-MM-DD)

YELLOW (N)
- [yel-1] Duplicate subjects: [[Page A]] / [[Page B]] (different areas, same subject)
- [yel-2] Orphan: [[Page]] (0 inbound links)

BLUE (N) / GREEN (N)
- ...
```

## Rules

<HardGate>
1. Prune is read-only. Never modify any wiki page during a scan. (`lint --fix` is adapt's tool, not prune's.)
</HardGate>

2. Use `index.md` as the page inventory — do not scan the filesystem directly for page discovery.
3. Contract violations come from lint — fold them in by kind and id; never re-implement its checks by hand.

