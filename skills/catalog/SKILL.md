---
description: Files references from raw/references/ into wiki collections. Captures the original into the immutable library/, writes the collection page citing it, and lands each reference as one git commit.
---

# /callosum:catalog

**When to use:** You have files in `raw/references/` that need to be filed into the wiki.

**Goal:** Turn practical reference artifacts into properly structured wiki pages inside the right collection. Every file in `raw/references/` is something you act on — a checklist, a log, a guide, a procedure, a note, or any other practical artifact. Catalog's job is to file it where it can be found and used again.

## Process

1. **Scan** `raw/references/` for files.
2. **Read** each file fully — partial reads produce wrong placement decisions.
3. **Capture into the library** — copy the original verbatim to `library/<slug>.<ext>`. The library copy is permanent and immutable. Then remove the original from `raw/references/`.
4. **Infer the artifact type and collection** from the content. Ask: what reusable kind of thing is this? Coin a plural collection label from that answer. Never choose from a fixed list and never require the type to have appeared before. If the artifact has no clear reusable kind, use the generic `notes` collection. Materialize it with `python3 "$CALLOSUM_PLUGIN_ROOT/scripts/emergent_collection.py" <mind-root> "<inferred plural label>"`; use the returned path. Set `type:` to the singular artifact kind and `domain:` to what the content is about; type and domain are separate decisions.
5. **Check existing wiki** — read `index.md` to see if a relevant page already exists.
   - Existing page, content adds to it → extend body or append entries.
   - No existing page → create new.
6. **Write** the page with frontmatter appropriate to its type (see AGENTS.md), with `sources` pointing at the library copy (`library/<slug>.<ext>`). Collection pages have free body structure — the page looks like whatever it is.
7. **Cross-link** only when there is a genuine semantic relationship — shared subject matter, direct reference, or meaningful contrast. Do not link pages merely because they share a domain or appeared in the same batch.
8. **Land** — once per reference:
   `python3 "$CALLOSUM_PLUGIN_ROOT/scripts/land_run.py" --actor catalog --source <slug> <files you created>`

## Rules

<HardGate>
1. Always capture the original into `library/` before writing its wiki page, and cite it in the page's `sources`. Never edit, move, or rename anything already in `library/`.
2. If a file is not a practical artifact, follow the Unprocessable Files protocol in AGENTS.md instead — do not capture it into the library.
</HardGate>

3. Collection pages are **data** — free-form body, no Timeline/anchors/citations ever. Still give them `title`, `type`, `domain`, `tags`, and the `sources` library pointer (that's what plugins consume), `synthesized: false` for human-written content, and no invented frontmatter fields beyond those. Do NOT author `last-updated` or touch `index.md`/`log.md` — hooks own bookkeeping.
