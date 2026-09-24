---
description: Research engine. Answers open questions and writes findings to the wiki.
argument-hint: <path | direct text>
---

# /callosum:investigate

**When to use:** You want to deeply research a specific question.

## Arguments

- **Path** — read the question from the given file (detect: argument looks like a filesystem path)
- **Direct text** — treat the argument as the research question itself
- If no argument is given, list available questions in `raw/questions/` and ask the user which one to investigate.

## Process

1. **Get the question** — read the question file fully, or use the direct text as the query. Question files may include context, constraints, and background; read all of it.
2. **Internal search** — scan `index.md` and read relevant wiki pages for existing knowledge on the topic.
4. **External research** — use web search to gather outside information, verify facts, and expand beyond internal knowledge. If unavailable, synthesize from internal content only and note the limitation.
5. **Synthesize** — produce a comprehensive research document at `wiki/research/<category>/[topic].md` (coin a category subdir) that directly answers the question. Research pages follow the knowledge-page contract: Compiled Truth claims each end with `[[#^tN]]`, and Timeline entries carry `Source:` lines — web URLs are valid sources for research pages; wiki pages consulted go into `derived_from` frontmatter (with their current `last-updated` as `observed`) so staleness is computable.
6. **Cross-link** — identify existing concept or entity pages that should reference this research; surgically add `[[WikiLinks]]` to them without overwriting any existing content. (Never modify `type: idea` pages — propose instead.)
7. **Archive** the original question file (if applicable) to `archive/questions/`.
8. **Land** — `python3 "$CALLOSUM_PLUGIN_ROOT/scripts/land_run.py" --actor investigate --source <topic-slug> <files>`

## Rules

<HardGate>
1. Always produce a research page — even if external search is unavailable, synthesize from internal knowledge and note the limitation.
2. Always use specific, disambiguated filenames for any new wiki pages (e.g., `tardigrade_cryptobiosis_mechanism.md`, not `survival.md`).
3. Never overwrite an existing page to add a cross-link — surgically append the link only.
</HardGate>

4. Do NOT author `last-updated` or touch `index.md`/`log.md` — hooks own bookkeeping.
