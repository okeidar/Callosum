---
description: Show recipes, record liked/did-not-like feedback, and find recipes by ingredients from the mind's emergent recipe collection.
argument-hint: <show|mark|find> <recipe or ingredients>
---

# /recipe-memory

This addon consumes `wiki/recipes/`, an ordinary collection that `/callosum:catalog` may infer
from the content. The addon does not create or teach that collection to core Callosum.

## Show

For `show <name>`, read the matching page in `wiki/recipes/`. Return its ingredients, method,
latest feedback, notes, and page path. If several titles match, ask rather than guessing.

## Find by ingredients

For `find <x, y, z>`, run `serve.py --reindex`; the deterministic index supplies the bounded
candidate set, then the underlying model ranks it semantically. Match synonyms, forms, culinary
equivalents, and query translations (queries may be any language while stored content stays
English). On true culinary ties prefer LIKED, then UNRATED, then DID_NOT_LIKE. Render the model's
short reason, matched query terms, unmatched query terms, verdict, and page path. Never claim an
ingredient is present without support in the candidate's `## Ingredients` list. If no model host
is executable, timeouts, or returns invalid output, fall back to exact matching and label the
result `Model host unavailable; exact ingredient matching only.`

## Mark feedback

For `mark <name> liked|did-not-like [notes]`:

1. Resolve exactly one page and preserve its current bytes as the edit base.
2. Append a dated, uniquely anchored entry to `## Timeline`:
   `### [YYYY-MM-DD] - Recipe verdict: LIKED ^tN` or `DID_NOT_LIKE`, then
   `Source: user-feedback` and the user's notes in English.
3. Update one line in `## Compiled Truth` so the current verdict cites that new anchor. Keep all
   earlier Timeline entries. Do not copy general food or pantry knowledge; link the existing
   page when it is genuinely related.
4. Run the exact edit through the prewrite gate. If allowed, write, run postwrite, land only the
   explicit touched files, then run `serve.py --reindex`.

<HardGate>
- Never edit a retained original in `library/`.
- Never manufacture feedback or notes.
- All stored text is English; transliterate proper names.
- Never expose pages tagged `sensitive` or `private`.
</HardGate>
