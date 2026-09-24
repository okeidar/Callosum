# Mind Wiki Contract

This file defines what a **well-formed** mind wiki is. It is the single source of truth for
validation: the prewrite gate blocks writes that violate a BLOCK rule; `lint` re-checks the
whole tree and reports WARN rules. Prose guidance for agents lives in `AGENTS.md`; this file
is the schema.

Contract version: **2.1**. Pages written before v2 (no `^tN` anchors) are *legacy*: lint reports
them as `legacy_uncited` (info), and the gate does not retroactively block them. Any page that
carries anchors is held to the full v2 rules.

## 1. Directory layout

```
<mind-root>/
├── .callosum              # marker file — identifies the mind root
├── AGENTS.md              # agent operating guide (prose)
├── wiki-contract.md       # this file
├── index.md               # GENERATED — one line per wiki page (hook-maintained)
├── log.md                 # GENERATED — append-only write ledger (hook-maintained)
├── raw/                   # ingest queues (pre-processing; files here are unvalidated)
│   ├── inbox/             # unsorted drops → /classify
│   ├── sources/           # knowledge to distill → /absorb
│   ├── ideas/             # ideas awaiting /callosum:incubate
│   ├── questions/         # questions awaiting /investigate
│   ├── references/        # practical artifacts awaiting /catalog
│   └── inconclusive/      # unprocessable files + <name>.meta.md sidecars
├── library/               # IMMUTABLE captured sources — see §2
├── archive/               # processed queue items (ideas/questions/references only)
│   ├── ideas/
│   ├── questions/
│   └── references/
└── wiki/                  # derived pages — the knowledge layer
    ├── entities/<category>/<slug>.md
    ├── concepts/<category>/<slug>.md
    ├── research/<category>/<slug>.md
    ├── synthesis/<category>/<slug>.md
    ├── ideas/<idea-name>/<idea-name>.md   (+ conditional/, rejected/)
    └── <domain>/<slug>.md                 # arbitrary data collections, coined on demand
```

Type folders (`entities/`, `concepts/`, `research/`, `synthesis/`) use categorical subdirs:
pages live at `wiki/<type>/<category>/<slug>.md`, never at the type root. Even a singleton
page gets a category.

## 2. Library — the source layer

`library/` holds captured sources **verbatim and permanently. Nothing in `library/` is ever
moved, renamed, or edited after capture** — this is what keeps every citation resolvable
forever.

Two unit shapes, decided at capture time (byte size first, then a cheap structure peek):

- **Flat source** — `library/<slug>.<ext>` — fits in one absorb pass; distilled fully.
- **Book** — `library/<slug>/book.md` + `library/<slug>/index.md` (table of contents) — too
  large to distill in one pass; absorb maps it shallowly from the TOC, `/callosum:recall` and
  `/callosum:librarian` drill specific chapters later via locators. TOC lines are pinned:
  `- <chapter-slug>: <chapter title>`, one per chapter, where each slug is the GitHub-style
  slug of a real heading in `book.md` (lint checks TOC↔heading agreement:
  `book_toc_missing` / `book_toc_mismatch`).

Legacy paths: `archive/sources/` and `wiki/sources/` are retired for new sources. Existing
files there remain valid citation targets (never move them either); lint reports pages citing
them as `legacy_source_location` (info).

**Distillation tracking:** a library item cited by zero wiki pages is un-distilled — a
deterministic lint check (`library_orphan`), not a status flag.

## 3. Page families and frontmatter

The contract's structure rules govern the **reserved folders only**: `wiki/entities/`,
`wiki/concepts/`, `wiki/research/`, `wiki/synthesis/`, `wiki/ideas/`. Pages there start with
YAML frontmatter:

```yaml
title:          # human title
type:           # closed set: entity | concept | principle | research | synthesis | idea
domain:         # knowledge domain (software-engineering, personal, …)
tags: []        # freeform, for apps/agents
last-updated:   # YYYY-MM-DD — STAMPED BY THE HOOK; agents never author or edit it
synthesized:    # true = agent-generated/altered; false = primarily human-written
```

Additional per family:

| Family | Types | Extra required | Extra optional |
|---|---|---|---|
| Knowledge | entity, concept, principle | `sources`, `related-pages` | — |
| Derived | research, synthesis | `sources`, `related-pages` | `derived_from` (§6) |
| Idea | idea | `verdict`, `date` | `related-pages` |

Do not invent frontmatter fields beyond this contract on governed pages — the frontmatter is
the API plugins read; ad-hoc keys are noise.

Type↔folder agreement is enforced: `type: entity` must live under `wiki/entities/`, ideas
under `wiki/ideas/`, etc.

**Everything else under `wiki/` is arbitrary data — not governed by this contract.** Any
other folder (`wiki/<domain>/`, coined organically as content shows up) holds free-form data
pages: the thing itself, in whatever shape suits it. No required frontmatter, no sections,
no citations — the citation machinery (§4) exists for *claims distilled from sources*, and a
data page is not a claim. Only the universal rails (§9) apply. Frontmatter
(`title`/`type`/`domain`/`tags`, plus a `sources` pointer when a library original exists) is
*recommended* because it is what plugins consume — lint nudges (info), never blocks.

## 4. Page body structure

**Knowledge and Derived pages** use two sections, in this order:

```markdown
## Compiled Truth
<current understanding — rewritten freely as evidence arrives>

## Timeline
<append-only evidence log — entries are never edited or deleted, only appended>
```

**Timeline entry format (v2):**

```markdown
### [YYYY-MM-DD] — Source Title ^t3
Source: [library/<slug>.md](library/<slug>.md)          # resolvable, mind-root-relative
Locator: ch2                                            # optional — book chapter / line span
- extracted fact
- extracted fact
```

- Each entry heading ends with a unique block anchor `^tN` (N increments; never reused).
- `Source:` must resolve to an existing file under the mind root.
- `Locator:` (optional) names a book chapter slug (`ch2`, `<chapter-slug>`) or line span (`L10-40`).
  The gate validates locators at write time: a chapter slug must exist in the book's TOC
  (`locator_unknown_chapter`; chapter form is invalid on flat sources) and a line span must
  fit the source file (`locator_span_out_of_range`).

**Compiled Truth citation rule (v2):** every claim is one line ending with its citation(s)
`[[#^tN]]`. A claim supported by several entries cites several anchors.

**Contested claims:** when sources genuinely conflict, keep BOTH Timeline entries, and render
in Compiled Truth exactly one single-sentence claim marked `[CONTESTED]` that cites **both**
anchors and elects no winner:

```markdown
[CONTESTED] Source A reports X while source B reports Y [[#^t2]] [[#^t5]].
```

Branching a page on contradiction is superseded — contradictions live on one page.
A `[CONTESTED]` marker clears only when a human resolves it (a Timeline entry stating the
resolution, `synthesized: false` edit, or via approved `/callosum:adapt`).

**Idea pages** keep their own structure (original content preserved in full + appended
`## Verdict` block with `### Basis` listing each basis page with its `last-updated` at verdict
time) — see `wiki/ideas/AGENTS.md`. Ideas are data: no anchors, no citations.

## 5. Linking rules

- Inline links use `[[slug]]` form (or `[[Title|display]]`); path-form inline links are
  normalized to slug form by the postwrite hook.
- `related-pages` frontmatter is reserved for **structural** relationships (built-on, port-of,
  foundation-of, instance-of, contains, subtype-of) and must be bidirectional: both pages list
  each other AND carry an inline link in the relevant body section. Co-mention in one source
  is not grounds for a link — that comparison belongs on a research/synthesis page.
- Links resolve to pages, never folders. Unresolved `related-pages` links are a lint WARN
  (`page_link_unresolved`) — not a write-time block, because a batch may create the target
  later in the same run.

## 6. Derived pages and staleness

`research` and `synthesis` pages record what they were derived from:

```yaml
derived_from:
  - page: wiki/entities/harnesses/claude-code.md
    observed: 2026-05-18        # that page's last-updated when this was derived
```

Staleness is **computed at read time**: a derived page is stale when any `derived_from` page's
current `last-updated` is newer than `observed`. Refresh is deferred — `/callosum:recall` re-derives on
next use; `/callosum:prune` flags (`stale_synthesis`); nothing eagerly recomputes.

Idea verdicts use the same mechanism through their `### Basis` section: any basis page updated
after the verdict `date` ⇒ stale verdict (`stale_verdict`).

## 7. Generated artifacts

`index.md` and `log.md` are maintained exclusively by the postwrite hook. Agents and skills
**never write them directly** — the gate blocks such writes. `lint --fix` regenerates them
from the tree.

## 8. Protected zones

- **`library/`** — write-once. The gate blocks edits to existing library files (capture of a
  new file is allowed).
- **`wiki/ideas/` autonomy** — skills must not unilaterally modify an existing `type: idea`
  page based on newly absorbed content. The gate blocks edits to existing files under
  `wiki/ideas/` unless `CALLOSUM_ALLOW_IDEA_WRITE=1` is set (used by `/callosum:incubate` when
  publishing, and by `/callosum:adapt` after explicit human approval). Creating a new idea page is
  always allowed. Cross-links into ideas follow the same rule: propose, don't push.
- **Timeline append-only** — an edit that removes an existing `^tN` anchor from a page is
  blocked.

## 9. Secrets

No page or library item may contain credential material. The gate blocks writes containing
obvious secrets (AWS access keys, PEM private-key blocks, bearer tokens, `api_key=`-style
assignments with literal values). Emails and names are fine — this is a personal wiki.

## 10. Enforcement summary

**Gate (prewrite hook — BLOCKS, fails closed):**
on reserved-folder pages: frontmatter parses · required fields present · type in closed set ·
type↔folder agreement · CT before Timeline on knowledge/derived pages · anchored pages keep
v2 citation rules · `[CONTESTED]` cites ≥2 anchors · Timeline anchors never removed ·
`Source:` paths resolve. Everywhere: no writes to `index.md`/`log.md` · library write-once ·
idea-page autonomy · nested-mind-root paths · no secrets. Data folders: secrets only.

**Lint (CLI — reports; `--fix` heals generated artifacts):**
everything the gate checks, plus: `page_link_unresolved` · `body_link_unresolved` (body
`[[links]]`, governed folders only) · `related_pages_not_bidirectional` ·
`library_orphan` · `stale_synthesis` · `stale_verdict` · `legacy_uncited` ·
`legacy_source_location` · `index_drift` (fixable) · `book_toc_missing` / `book_toc_mismatch`.
Lint can be scoped: `--changed [REF]` (git-dirty pages) or `--recent DAYS` (pages whose
`last-updated` is within DAYS) — scoped passes run per-page checks only; tree-level checks
are full-pass by nature. `/callosum:prune --recent` consumes `--recent 7`.

**The rule that governs the split:** a job is a script only if it is deterministic; anything
needing judgment belongs to a skill (`/callosum:prune` diagnoses, `/callosum:adapt` repairs, humans decide).

## 11. Extensible governance

Scope is decided by **one resolver** (in `scripts/checks.py`), consumed by both the gate and
lint — the two must never grow separate ideas of what is governed.

- **Govern by default:** every write under the mind root is governed. Universal checks
  (secrets) apply to *every* file and can never be opted out. Contract/structure checks apply
  to `wiki/` pages per their type-derived profile.
- **Per-folder declaration:** a folder under `wiki/` may carry a `.callosum-profile` file that
  re-profiles or exempts its contents — this is how plugins register new governed areas
  without patching base code:

  ```yaml
  profile: knowledge    # knowledge | data | idea | exempt
  disable: [missing_category_subdir]   # named checks to turn off for this folder
  ```

  `exempt` keeps only the universal checks; `data` is the default for any non-reserved folder
  (declaring it is only needed to override). A declared folder owns its own placement rules
  (type↔folder agreement is skipped). Most folders need no declaration — the defaults are the
  profile.
- **Failure mode is loud and safe:** an undeclared new folder is governed under the default
  rules (a blocked write with a clear message), never silently un-governed.

