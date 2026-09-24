# Callosum

Callosum is a local, git-backed knowledge system for Claude Code. It turns an inbox of
sources, notes, questions, and ideas into a durable wiki while keeping the original material
and, for governed knowledge pages, the evidence behind each claim.

Used through the bundled `mind` agent, it can act as an offloaded context layer: consult the
wiki before answering, return cited stored context, and route new material into the ingest path.
An honest miss stays an honest miss instead of being filled from the model's memory.

The core does not hardcode content types. Knowledge pages use a checked contract; everything
else under `wiki/` can take the shape the content needs. Optional addons read those derived
pages or trigger a closed set of Callosum skills.

## Requirements

- Python 3.9 or newer
- Git
- Claude Code with plugin commands available

Callosum has no runtime Python dependencies.

## Install

Clone the repository, then run:

```bash
python3 setup_claudecode.py
```

This installs the Callosum plugin for the current user and creates `~/mind` from the starter
template. It will not overwrite an existing mind.

To use another location:

```bash
python3 setup_claudecode.py /path/to/mind
```

To update Callosum-owned infrastructure in an existing mind without touching its content:

```bash
python3 setup_claudecode.py --refresh /path/to/mind
```

Set `CALLOSUM_MIND_ROOT` when the mind is not `~/mind` and you invoke Claude Code outside it.

For OpenClaw, run `python3 setup_openclaw.py`. That links only the Callosum plugin; it does not
change your model, provider, workspace, or other OpenClaw settings.

## First run

Start Claude Code in the mind directory and try:

```text
/callosum:status
/callosum:classify
```

Put incoming material in `raw/inbox/`. Callosum routes and processes it with these skills:

- `/callosum:classify` routes inbox files
- `/callosum:catalog` files references as useful data
- `/callosum:absorb` extracts grounded knowledge from sources
- `/callosum:recall` answers from the wiki and retained originals
- `/callosum:investigate` researches open questions
- `/callosum:incubate` develops ideas into evidence-backed verdicts
- `/callosum:prune` reports health problems; `/callosum:adapt` fixes only after approval
- `/callosum:status` shows the current health snapshot
- `/callosum:librarian` retrieves passages from retained books without loading a whole book

Every knowledge write made by a Callosum skill passes through the contract gate and post-write
bookkeeping. Each processed source is landed as its own local git commit when the mind is a git
repository.

## Check a mind

```bash
python3 -m scripts.lint ~/mind
python3 -m scripts.lint ~/mind --fix
```

`--fix` regenerates derived bookkeeping only. It does not rewrite knowledge.

## Addons

```bash
python3 -m scripts.install_addon --list
python3 -m scripts.install_addon <addon-name>
```

UI addons run from this repository. The installer checks declared prerequisites and prints
their exact command; UI-only addons copy no files. See [`examples/README.md`](examples/README.md)
for the addon contract and examples.

Export a searchable static snapshot after mind changes with:

```bash
python3 -m scripts.export_static_ui /path/to/mind
```

## Verification

This is a product export. Automated checks and development history remain in the private
workspace and are not included here. Installation and hook behavior should be checked in
Claude Code or OpenClaw on the machine where the plugin is used.

## Product guidance

- [`CLAUDE.md`](CLAUDE.md) - operating model and skills
- [`template/wiki-contract.md`](template/wiki-contract.md) - wiki page contract
- [`examples/README.md`](examples/README.md) - optional addon examples

## License

Callosum is released under the [MIT License](LICENSE).
