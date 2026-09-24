---
description: Example Callosum plugin — find something to cook from the recipes in the mind wiki, given ingredients on hand. Reads DERIVED pages (wiki/recipes/) only; never library originals. Read-only.
argument-hint: <ingredients you have>
---

# /recipe-finder

**What this is:** an example of a Callosum L4 plugin — a projection over derived wiki pages.
It owns no data and writes nothing; the wiki collection pages are its entire data layer.

**When to use:** "What can I cook with X, Y, Z?"

## Process

1. Resolve the mind root: `$CALLOSUM_MIND_ROOT`, else nearest `.callosum` ancestor, else `~/mind`.
2. List `wiki/recipes/*.md`. If the collection is empty, say so and suggest `/callosum:catalog` for any
   recipe files waiting in `raw/references/`.
3. Read each recipe page — frontmatter (`title`, `tags`) and its ingredients section.
4. Rank recipes by how many of the user's ingredients they use, noting what's missing for each.
5. Answer: the best match (with why), runners-up, and each recipe's missing ingredients.
   Reference pages as `wiki/recipes/<name>.md` so the user can open them.

## Rules

<HardGate>
1. Read-only. Never write, move, or edit any file.
2. Read derived pages only (`wiki/recipes/`). Never open `library/` originals or `raw/` queues —
   if a recipe page seems incomplete, say so; do not go around it.
</HardGate>
