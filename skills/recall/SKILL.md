---
description: Queries the wiki and synthesizes answers — synthesis cache first (freshness-checked), then wiki pages, then library deep-dive. Writes derived insights back (with derived_from staleness tracking) so future queries need no reasoning turns.
argument-hint: <query>
---

# /callosum:recall

**Goal:** Synthesize what the wiki already knows in response to a question, then write any derived insight back so future queries get the answer directly from the document — no reasoning turns required. The wiki should be smarter after every recall run than it was before.

**When to use:** You want to query what you know about a topic.

## Arguments

- **Query text** (required) — the topic or question to look up. If none provided, ask for one.

## Process — three layers, cheapest first

1. **Parse** the query — identify key terms, entities, and domain signals.

2. **Layer 1 — synthesis cache.** Check `wiki/synthesis/` (via `index.md`) for a page that already answers this. If found, **check freshness**: for each entry in its `derived_from` frontmatter, compare `observed` against that page's current `last-updated`.
   - All fresh → answer from it directly. Done.
   - Stale → keep its `derived_from` list as the starting page set and re-derive (continue below).

3. **Layer 2 — wiki pages.** Search `index.md` — match by domain, tags, type, and keywords in titles and summaries. Read the relevant pages; prioritize domain match > tag match > keyword match. Read as many as needed to answer well; note if you excluded relevant pages due to context limits.

4. **Layer 3 — library deep-dive.** If the pages don't fully answer but their Timelines cite a library **book** (`Source:` into `library/<slug>/` with a `Locator:`), drill it through `/callosum:librarian` (TOC first, relevant chapters only — never the whole book). Facts you surface this way are candidates for a later `/callosum:absorb` pass onto the covering page; mention that to the user rather than writing wiki pages yourself.

5. **If nothing relevant found** — report clearly that the topic isn't in the wiki yet. Offer to run `/callosum:investigate` to research it.

6. **Synthesize** a direct answer from the gathered material and **present** it with inline source references.

7. **Write the insight back** if the answer required any derivation — even from a single page. Ask: is this answer directly readable from the wiki right now, or did it require reasoning?
   - If it required reasoning, propose the target and the text:
     - **Same page** — if the insight is a natural addition to an existing page's Compiled Truth (cite existing Timeline anchors).
     - **New synthesis page** — `wiki/synthesis/<category>/<slug>.md` if it stands alone across topics. Record provenance in frontmatter so staleness is computable:
       ```yaml
       derived_from:
         - page: wiki/entities/harnesses/claude-code.md
           observed: 2026-05-18   # that page's last-updated right now
       ```
   - Write only on explicit user confirmation. Then land it:
     `python3 "$CALLOSUM_PLUGIN_ROOT/scripts/land_run.py" --actor recall --source <query-slug> <files>`
   - If the answer was already directly readable from the wiki, no write-back needed.

## Source Precedence

When sources conflict, trust in this order:
1. User statements in the current conversation
2. Compiled Truth sections
3. Timeline sections
4. External sources

If Timeline sections contain unresolved contradictions (`[CONTESTED]` claims), surface the conflict rather than picking a side.

## Rules

<HardGate>
1. Never write back to the wiki without explicit user confirmation.
2. Never present a synthesized answer as settled fact if its sources contain unresolved contradictions — surface the conflict instead.
3. Never write into `library/` — it is read-only for recall.
</HardGate>

4. Do NOT author `last-updated` or touch `index.md`/`log.md` — hooks own bookkeeping.

