# Idea Documents

## Idea Lifecycle

1. **Raw idea** — captured in `raw/ideas/<name>.md`. Either written directly by a human, or created by `/callosum:absorb` when a source describes a project to build. Contains the original idea content only; no verdict yet.

2. **Enriched idea** — `/callosum:incubate` processes raw ideas, appends a verdict section, and moves the file to its destination in `wiki/ideas/` (ripened to its own subdir, or to `conditional/`, or to `rejected/`).

Documents in `wiki/ideas/` are **enriched idea files** — the original raw idea preserved in full, with a verdict section appended by `/callosum:incubate`. The original content is never summarized or replaced; it remains the primary value of the document.

- **Ripened ideas** (`wiki/ideas/[name]/[name].md`) are full project seeds — the complete idea content plus verdict is what gets recalled and used to start work.
- **Rejected ideas** (`wiki/ideas/rejected/`) preserve full context for pattern-matching when similar ideas arise later.
- **Conditional ideas** (`wiki/ideas/conditional/`) preserve full context alongside the specific blockers that must be resolved.

## Required Frontmatter

```yaml
---
title: Idea Name
type: idea
verdict: RIPENED | REJECTED | CONDITIONAL
date: YYYY-MM-DD
domain: relevant-domain
tags: [tag1, tag2]
related-pages:
  - "[[Related Page]]"
last-updated: YYYY-MM-DD
synthesized: true
---
```

## Document Structure

```markdown
[FULL ORIGINAL IDEA CONTENT — preserved exactly as written by the human]

---

## Verdict: RIPENED | REJECTED | CONDITIONAL

**Date:** YYYY-MM-DD
**Complexity:** Low | Medium | High
**Principle alignment:** [brief note on fit or conflict with personal principles]

### Reasoning
[Why this verdict was reached]

### Key Findings
[What research surfaced that wasn't in the original idea — prior art, known pitfalls, market context, technical constraints]

### Basis
- [[Wiki Page]] (last-updated: YYYY-MM-DD)
- [[Another Page]] (last-updated: YYYY-MM-DD)

### Conditions
[If CONDITIONAL: specific blockers — concrete decisions or facts needed, not vague concerns]
```

## Staleness

If any page listed in **Basis** is updated after the verdict `date`, `/callosum:prune` will flag this document as stale for re-evaluation.
