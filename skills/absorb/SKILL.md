---
description: Processes sources from raw/sources/ into wiki pages. Captures each source into the immutable library/, extracts entities, concepts, relationships, and ideas into cited pages, and lands each source as one git commit. Makes smart decisions about create vs update.
---

# /callosum:absorb

**Goal:** Turn raw external sources into compiled wiki knowledge. Capture the source into the library, extract everything worth keeping — entities, concepts, relationships, ideas, and any embedded practical pages — and integrate it into the wiki with every claim cited. The wiki should be smarter after every absorb run than it was before.

**When to use:** You have files in `raw/sources/` ready to be processed.

## Process

1. **Scan** `raw/sources/` for files.

2. **Capture into the library** — before reading deeply, decide the source's shape by bytes on disk first, structure second:
   - **Flat source** (fits in one distillation pass): copy verbatim to `library/<slug>.<ext>`.
   - **Book** (too large for one pass — multi-hundred-page papers, large dumps, chaptered material): place as `library/<slug>/book.md` and write `library/<slug>/index.md` — a table of contents mapping chapter slugs to the book's headings.
   - The library copy is **permanent and immutable** — never edited, moved, or renamed after this step. Then remove the original from `raw/sources/` (its content now lives in the library).

3. **Read** the source from the library.
   - Flat sources: read fully — do not sample or truncate.
   - Books: read the TOC and the most relevant chapters; extract what you can and leave the rest — `/callosum:recall` drills specific chapters later by locator. Do not try to exhaust a book in one pass.
   - For **conversation-shaped sources** where the absorb agent participated in the dialog (JSONL transcripts of the current session), the in-context conversation IS the source — re-reading the file is redundant.

4. **Analyze** — identify all wiki-worthy content: entities, concepts, relationships, ideas, and any embedded practical pages (procedures, logs, reference cards, or whatever the domain produces). A single source can yield multiple pages of different types. **Also classify the source's framing** (technical research, competitive/market research, domain reference, idea capture, etc.) — framing drives subfolder choice, not filename or topic.

5. **Match before you create** — read `index.md` AND walk the relevant `wiki/<type>/` category folders for each subject you plan to write. An existing page under a different name or category beats a new parallel page: append to its Timeline and cross-link instead. Only after this walk may you create a page.

6. **Decide** for each piece of content:
   - Not in wiki → create new page.
   - Exists → append a Timeline entry; revise Compiled Truth only if the new source materially adds to it.
   - Related but distinct → create new page, link if structurally related.
   - Contradicts existing knowledge → see Contradictions below. Never silently overwrite Compiled Truth.

7. **Write** pages per the contract (`wiki-contract.md` at the mind root — the gate enforces it):
   - Timeline entries are append-only, each heading ending with the next block anchor:
     `### [YYYY-MM-DD] — Source Title ^tN`, followed by `Source: [library/<slug>.md](library/<slug>.md)` (and `Locator: <chapter-slug>` for book extracts).
   - Every Compiled Truth claim is **one line ending with its citation(s)** `[[#^tN]]`. Never leave a claim uncited.
   - `entity`, `concept`, `principle`, `research`, `synthesis` → `wiki/<type>/<category>/<name>.md`. Coin a category folder when content warrants it (e.g. `entities/harnesses/`, `research/coding-agents/`). Singleton pages still get a category folder.
   - `idea` → `raw/ideas/<name>.md` (NOT `wiki/ideas/`). `/callosum:incubate` ripens raw ideas into `wiki/ideas/` with a verdict. Absorb captures the original idea content only.
   - Domain-specific collections (any topic the source is about) → `wiki/<domain>/<name>.md`, folder and `type:` coined from the content. These are **data pages**: free body structure, NO Timeline/anchors/citations (the thing itself, not an argument), just `title`/`type`/`domain`/`tags` + `sources` pointing at the library item, and no invented frontmatter fields.
   - Entity pages describe the entity **standalone** — intrinsic claims only. Peer-relative claims (rankings, "the most X in the category") go on research/synthesis pages.

8. **Contradictions** — when a new source conflicts with an existing Timeline entry: append the new entry anyway (both sides stay), and rewrite the affected Compiled Truth claim as **one single sentence marked `[CONTESTED]` citing both anchors**, electing no winner:
   `[CONTESTED] Source A reports X while source B reports Y [[#^t2]] [[#^t5]].`
   Never branch a page over a contradiction; never drop either side. Only a human clears the marker.

9. **Verify cross-references**: every `[[wikilink]]` in body text either resolves to a real page or is an explicit forward reference for a future absorb to fill. Structural links (built-on, port-of, instance-of, contains, subtype-of) must appear in both pages' `related-pages` frontmatter AND as inline `[[WikiLinks]]` in the relevant body section.

10. **Land** — final step, once per source:
    `python3 "$CALLOSUM_PLUGIN_ROOT/scripts/land_run.py" --actor absorb --source <slug> <every file you created or edited>`
    One commit per source, explicit file list. Never use `git add -A` or commit by hand.

## Rules

<HardGate>
1. Never overwrite Compiled Truth when a source contradicts it. Keep both Timeline entries and render one `[CONTESTED]` claim citing both anchors.
2. Every source is captured into `library/` before its facts are written, and every Timeline entry cites its library `Source:` path. Never leave a source stranded in `raw/sources/`, and never edit, move, or rename anything already in `library/`.
3. Match before you create: no new page without first checking `index.md` and walking the relevant category folders for an existing page on the same subject.
</HardGate>

4. Page format and frontmatter schema are defined in `wiki-contract.md` and AGENTS.md — follow them exactly. Do NOT author `last-updated`, and do NOT touch `index.md` or `log.md` — hooks own all bookkeeping (the gate will block you).

5. **Cross-link only on real structural or conceptual relationships** (built on, port of, foundation of, instance of, contains, subtype of). Do **not** link pages together solely because they appeared in the same source — that comparison belongs on a research or synthesis page, which both link to. When a link IS structural, it must be bidirectional: appear in both pages' `related-pages` frontmatter.

6. Never modify an existing `type: idea` page based on absorbed content — propose the change to the user instead (the gate blocks unilateral idea writes).
