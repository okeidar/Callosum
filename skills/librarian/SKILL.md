---
description: Read-only access to library books (library/<slug>/book.md). Answers questions or retrieves passages by drilling chapters through the book's TOC — never loads a whole book, never writes anything. Use when a question needs primary-source material that wiki pages have not distilled yet.
argument-hint: <book-slug> [question or chapter]
---

# /callosum:librarian

**Goal:** Answer from the library's books without exhausting them. Books are ground truth that `/callosum:absorb` only mapped shallowly — the librarian is how you drill one chapter on demand. Distilling what you find into wiki pages is `/callosum:absorb`'s job, never this skill's.

**When to use:** A `/callosum:recall` Layer-3 dive, or any direct question about a book's contents.

## Arguments

- **book-slug** (required) — the `library/<slug>/` directory. If omitted or unmatched, list the available books (`library/*/book.md`) and ask.
- **question or chapter** (optional) — what to look for. If omitted, present the TOC with a one-line orientation per chapter and stop.

## Process

1. **Open the TOC first** — `library/<slug>/index.md`, always. It maps chapter slugs to the book's headings (`- <chapter-slug>: <chapter title>`). Never open `book.md` before the TOC.
2. **Pick the chapter(s)** whose titles bear on the question. Prefer one; two or three when the question spans them.
3. **Read only those chapters** — locate the chapter's heading in `book.md` and read from it to the next heading of the same or higher level. Never read the whole book. (If the book is short enough to fit comfortably in one read, it would not have been captured as a book — treat the TOC as the contract anyway.)
4. **Answer** with the chapter slug as locator for every passage you use (`chapter-one`, `ch2`), so a later Timeline entry can cite `Source:` + `Locator:` and the gate can validate it.
5. **Surface, don't distill** — if what you found belongs in the wiki, say so ("candidate for /callosum:absorb onto [[page]]"); do not write it yourself.

## Rules

<HardGate>
1. Read-only: never write or edit any file — not the book, not the TOC, not the wiki, not `index.md`/`log.md`.
2. TOC first, chapters only — never load a whole book.
</HardGate>

3. If the TOC has no chapter matching the question, say so plainly and list what the TOC does offer. Do not skim the book "just in case" — that is the failure mode this skill exists to prevent.
