# Example plugins

Callosum plugins are **apps with a UI** whose data layer is the mind wiki's derived pages
(`wiki/`). The wiki contract (frontmatter as API) is what makes the pages consumable. A plugin
may ship an optional slash-command skill as its agent-side interface, but the plugin itself is
a UI. Two kinds:

- **Projection** (read-only) — displays derived pages; never writes, never reads `library/`
  originals or `raw/` queues. `recipe-book-ui/`, `idea-board-ui/`.
- **Actionable console** — a projection that can also *trigger a skill* on a user gesture (drag
  a card, click a button). It still **never writes the wiki itself** — it invokes a skill
  (`/callosum:incubate`, `/callosum:investigate`, …), which writes through the prewrite gate
  and lands a commit.
  UI gesture → skill → validated, durable knowledge. `idea-board-kinetic/`, `recipe-memory/`.

The rule that keeps actionable consoles safe: the plugin *requests* work from a **closed set**
of skill actions; it never composes wiki writes and never shells arbitrary commands. All the
substrate guarantees (contract gate, citations, per-source commits) hold because the write
still goes through a skill.

| Example | What it shows |
|---|---|
| `recipe-memory/` | Full recipe memory over an emergent `wiki/recipes/` collection: browse, ingredient index/search, latest liked/did-not-like state, and fixed skill-triggered feedback updates. Core Callosum does not name or pre-create the collection. `python3 examples/recipe-memory/serve.py [mind-root] --port 8769` |
| `recipe-book-ui/` | The canonical shape: `serve.py` renders a browsable, ingredient-filterable recipe book over `wiki/recipes/` (arbitrary data). Stdlib only. `python3 examples/recipe-book-ui/serve.py [mind-root]` |
| `recipe-finder/` | The agent-side companion: a read-only skill answering "what can I cook with X?" from the same derived pages. |
| `idea-board-ui/` | The idea pipeline's projection: a kanban over `wiki/ideas/` — columns are verdict states (RIPENED/CONDITIONAL/REJECTED), cards show a STALE badge when a `### Basis` page changed after the verdict. Read-only. `python3 examples/idea-board-ui/serve.py [mind-root] --port 8766` |
| `idea-board-kinetic/` | The **actionable** version: an Inbox column of raw ideas (`raw/ideas/`); drag a card into the **Incubate** or **Research** lane and the board runs `/callosum:incubate` or `/callosum:investigate` on it — the card then lands in the verdict column the skill decided. The board triggers skills; the skills do the writing. `python3 examples/idea-board-kinetic/serve.py [mind-root] --port 8767` |
| `idea-kanban/` | The full-pipeline console: **Queued → Ripening → verdict** columns. Runs are asynchronous — a dropped card moves to a live **Ripening** column while the skill works (several can ripen in parallel), then lands in the verdict column; a run that dies without a verdict is marked FAILED with its log tail. STALE verdict cards get a re-incubate button that hands the page path back to `/callosum:incubate`. Verdict columns beyond the declared RIPENED/CONDITIONAL/REJECTED are coined from the data itself. Run state lives in `.idea-kanban/` under the mind root, outside every governed folder. `python3 examples/idea-kanban/serve.py [mind-root] --port 8768` |

Two plugins over two different substrates — arbitrary data (recipes) and the opinionated idea
pipeline (verdicts + Basis staleness) — is what proves the model generalizes. A knowledge dashboard over `index.md` +
lint JSON is a natural third.

## Installing an addon

One command, generic (the installer inspects what a directory ships — a skill, a UI, or
both — and knows nothing about any addon's domain):

```
python3 -m scripts.install_addon --list          # what is available
python3 -m scripts.install_addon recipe-finder   # install its skill into ~/.claude/skills
```

UI-only addons do not copy anything into the mind or skills directory. The installer validates
declared runtime prerequisites, then prints the exact command that runs the UI from the current
Callosum clone. Actionable consoles such as `idea-kanban` require an executable `claude` CLI;
missing or non-executable hosts fail during preparation instead of at the first drag.

## Static mind viewer

Generate a self-contained, searchable snapshot without hand-editing `ui/data.json`:

```
python3 -m scripts.export_static_ui /path/to/mind
# writes /path/to/mind/ui/index.html and data.json
```

Re-run after mind changes. The exporter reads governed wiki pages, keeps Hebrew/Unicode text,
omits pages tagged `sensitive` or `private`, and never copies library source contents. Serve the
folder locally (for example `python3 -m http.server -d /path/to/mind/ui`) because browsers often
block `fetch()` from a direct `file://` open.

## The plugin contract

1. **Read derived pages** — `wiki/**` markdown + YAML frontmatter is the API
   (`type`, `domain`, `tags`, page body sections). For processing, an actionable console may
   also list a raw queue (e.g. `raw/ideas/`) as its "to do" column.
2. **Never write the wiki directly.** A projection writes nothing. An actionable console
   triggers a **skill** from a closed action set; the skill is what writes (through the gate,
   with a landed commit). The plugin never composes a wiki page and never shells an arbitrary
   command — actions map to fixed skill invocations, and any identifier passed in is validated
   and handed to the skill as an argument, never interpolated into a shell string.
3. **Register new governed areas via `.callosum-profile`** if the plugin needs its own
   folder under `wiki/` — never by patching Callosum's checks.
4. Resolve the mind root the standard way: `$CALLOSUM_MIND_ROOT` → nearest `.callosum`
   ancestor → `~/mind`.

