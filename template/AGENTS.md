# Mind Wiki -- Rules

The machine-checkable schema lives in [`wiki-contract.md`](wiki-contract.md) — the prewrite
gate and `lint` enforce it. This file is the prose guide: what goes where, and the judgment
rules that can't be automated.

## Page Format

Every knowledge page uses two sections:

- **Compiled Truth** (top): Current synthesis of understanding, revised as new information arrives. Every claim is one line ending with its Timeline citation(s) `[[#^tN]]`.
- **Timeline** (bottom): Append-only log of evidence. Never edited, only appended. Each entry heading carries a block anchor and cites its source file: `### [YYYY-MM-DD] — Source Title ^tN`, followed by a `Source:` line pointing into `library/`.

## Required Frontmatter (knowledge machinery pages)

Applies to pages in the reserved folders (`entities/`, `concepts/`, `research/`,
`synthesis/`, `ideas/`). Data pages elsewhere are free-form — frontmatter there is
recommended (it's what plugins read), never required.

```yaml
---
title: Page Title
type: entity | concept | principle | research | synthesis | idea
domain: domain-name
tags: [tag1, tag2]
sources:
  - library/source-slug.md
related-pages:
  - "[[Related Page]]"
last-updated: YYYY-MM-DD   # stamped by the hook — never author this yourself
synthesized: true | false
---
```

- `synthesized: true` -- page was generated or significantly altered by the agent
- `synthesized: false` -- page is primarily human-written
- `domain` -- the knowledge domain (e.g., software-engineering, cooking, personal)
- `tags` -- freeform tags for filtering by apps and agents

## Page Types

- **entity** -- Things: people, technologies, companies, tools, places, organizations → `wiki/entities/`. Describe the entity standalone — what it is, has, and does. An entity page should remain stable when new peers are added to the wiki: if adding a peer would force an edit here, that claim is peer-relative and belongs on a research or synthesis page instead. Intrinsic factual claims about the entity's nature (e.g. "black holes have the strongest gravitational fields in physics") are allowed; ranked comparisons against named or implied peers from the same wiki ("the highest compliance among LLM-obs vendors") are not. *Borderline test:* "Cycode ships an eBPF runtime sensor" is intrinsic — adding a new peer doesn't invalidate it. "Cycode has the most aggressive runtime bet" is peer-relative — route it to a research/synthesis page.
- **concept** -- Ideas: methods, patterns, theories, domains → `wiki/concepts/`
- **principle** -- Personal heuristics (subtype of concept) → `wiki/concepts/`
- **research** -- Investigations → `wiki/research/`. Where comparisons, evaluations, and market analyses live.
- **synthesis** -- Cross-domain connections → `wiki/synthesis/`. Where cross-cutting patterns spanning multiple entities or sources live.
- **idea** -- Ripened ideas (each gets its own subdirectory) → `wiki/ideas/[idea-name]/` — see `wiki/ideas/AGENTS.md`. Subject to Invariant Rule 6 — not unilaterally modified by skills.
- **Anything else is data** → `wiki/[domain-name]/`. Whatever topic shows up — the domain folder is coined on demand from the content. Free-form pages, not governed by the contract's structure rules: the page looks like whatever it is, no citations, no required sections.

## Folder Structure

```
library/                     # captured sources, verbatim, IMMUTABLE — nothing ever moves out
├── <slug>.md                # flat source (distilled fully in one pass)
└── <slug>/book.md + index.md  # large chaptered source (mapped shallowly; drilled on demand)

wiki/
├── entities/<category>/     # type: entity, grouped by category (e.g. harnesses/, frameworks/)
├── concepts/<category>/     # type: concept, principle
├── research/<category>/     # type: research
├── synthesis/<category>/    # type: synthesis
├── ideas/
│   ├── [idea-name]/         # ripened idea — own subdir per idea (post-/callosum:incubate)
│   ├── conditional/         # blocked ideas
│   └── rejected/            # dismissed ideas
└── [domain]/                # arbitrary data collections, coined on demand from content
```

Type-based folders use **categorical subdirs**: pages live at `wiki/<type>/<category>/<name>.md`, never directly at the type root. `/callosum:absorb` coins category folders when content warrants them. Even a singleton page picks a category.

Ideas keep the per-entry subdir pattern (`ideas/<idea-name>/<idea-name>.md`) because they may carry supporting artifacts. See `wiki/ideas/AGENTS.md`.

## Sources: the Library

Sources are captured into `library/` **once, verbatim, permanently** — they are never moved,
renamed, or edited afterward, so citations never break. Small sources land as flat files and
are distilled fully. Large sources (books, long papers, big dumps) land as `library/<slug>/book.md`
with a `library/<slug>/index.md` table of contents; `/callosum:absorb` maps them shallowly from the TOC
and `/callosum:recall` drills specific chapters later. Distillation progress is visible, not tracked:
a library item no wiki page cites yet is simply not distilled (lint reports it).

Plugins and apps read **derived wiki pages**, never library originals — the library exists for
grounding, citation integrity, and re-derivation.

## Domain Collections (arbitrary data)

The wiki holds domain data folders alongside the knowledge folders — one per topic that shows up, whatever it is. They are coined organically by `/callosum:absorb` or `/callosum:catalog` from the content, never pre-created, and the contract's structure rules don't apply inside them. Body structure is entirely free. When a page was derived from a captured file, give it frontmatter (`title`, `type`, `domain`, `tags`) and a `sources` pointer to the library item — that's what makes it consumable by plugins and traceable to its original — but a hand-written page with none of that is perfectly valid.

This is the point of Callosum: drop in anything and it's stored properly without being told in advance what "anything" is. The domain type (`type:`) and folder name come from the content itself.

## Tool Priority

Use the harness's native built-in tools for all operations (reading files, writing files, moving files, creating directories) when they exist. Only fall back to shell commands or scripting if no native tool covers the operation. Never write custom code to do something a built-in tool already handles.

## Invariant Rules

1. **Page creation threshold:** Create a new page when (a) the content has standalone substance (a paragraph of compiled truth or more), AND (b) the entity/concept will plausibly recur — a tool, framework, person, pattern, or term future sources are likely to mention. Otherwise, add the content as a section in the closest existing page. Co-mention in a single source is not, by itself, sufficient grounds for a page.
2. **Contradiction handling:** When source A says X and source B says Y, do NOT silently pick one, and do NOT branch the page. Keep both Timeline entries and render exactly one single-sentence `[CONTESTED]` claim in Compiled Truth citing both anchors, electing no winner. Only a human resolution clears the marker.
3. **Entity disambiguation:** Namespace ambiguous terms by domain -- `[[React (Software)]]` vs `[[Reactivity (Chemistry)]]`. Use Obsidian aliases for alternate names.
4. **Trust calibration:** All pages generated or significantly altered by the agent carry `synthesized: true` in frontmatter. This distinguishes your raw thoughts from AI-generated synthesis.
5. **Cross-references:** Cross-link only on real structural or conceptual relationships -- *built on*, *port of*, *foundation of*, *instance of*, *contains*, *subtype of*. Do NOT link pages together because they appeared in the same source -- that comparison belongs on a research or synthesis page, which both link to. When a link IS structural, it must be bidirectional: appear in both pages' `related-pages` frontmatter AND as an inline `[[WikiLink]]` in the relevant body section.
6. **Idea-page autonomy:** Skills must not unilaterally modify pages of `type: idea` (especially ripened ideas) based on newly absorbed sources. If new content bears on an idea, propose the change and ask the user for confirmation. Cross-links into ideas follow the same rule — propose, don't push. (Enforced by the gate; `/callosum:incubate` publishing and human-approved `/callosum:adapt` fixes are the sanctioned paths.)
7. **Match before you create:** Before creating any page, walk the relevant type folders and check `index.md` for an existing page covering the same subject under a different name or category. Prefer appending to and cross-linking the existing page over creating a parallel one.

## Bookkeeping is not your job

`index.md`, `log.md`, and `last-updated` stamps are maintained automatically by hooks. Never
write them yourself — the gate blocks it. Move files with native tools; the rails do the rest.

## Unprocessable Files

If any skill encounters a file it cannot process — wrong type for that skill, unreadable format, or ambiguous beyond resolution — move it to `raw/inconclusive/` and create a sidecar file `<original_filename>.meta.md` alongside it explaining why it wasn't processed. Never silently skip, delete, or leave a file stranded in its original location.

## Design Principle

Wiki content is structured for simultaneous consumption by:
- **Humans** -- readable in Obsidian, browsable by folder, searchable by tag
- **Agents** -- parseable frontmatter, consistent page format, machine-readable `index.md`
- **Apps** -- filterable by `type`, `domain`, `tags`; plugins (a board, a browser, a dashboard — whatever the data suggests) read derived wiki pages as their data layer — never library originals

This is why frontmatter fields (`domain`, `tags`, `type`) are mandatory, not optional -- they are the API for both agents and apps.

## Key Principle Pages

- [[Side Project Criteria]]
