---
description: Classifies inbox files to proper input type subfolders. Reads raw/inbox/, classifies as input type (source, idea, question, reference, etc), moves to appropriate subfolder.
argument-hint: [path | direct text]
---

# /callosum:classify

**When to use:** You have files in `raw/inbox/` that need routing to typed input directories.

## Arguments

This skill supports three invocation modes:

- **No argument** — process all files in `raw/inbox/` (default)
- **Path** — process all files found at the given path instead of the default inbox
- **Direct text** — treat the argument as raw content; classify it and create the file in the correct type subfolder. Detect by checking if the argument looks like a filesystem path (starts with a drive letter, `/`, `~/`, or `./`, or contains path separators) — if not, treat it as direct text. Derive a short kebab-case filename from the content.

## Goal

This is an entry point for callosum - a massive mind wiki. This step takes input artifacts from the inbox and classifies them into appropriate categories. Input may be anything — text files, images, PDFs, or direct text input. Each item contains information that should be classified into a type which will then be processed by a dedicated expert for that type.

## Types

- **sources** — anything whose primary value is knowledge or information about a topic that should be compiled into the wiki. Articles, papers, history, science, explanations, research. You learn *from* it.
- **ideas** — concepts, thoughts, hunches, half-baked ideas. The author has a direction — something to build, try, create, or experiment with. The file describes a concept or action, even if it contains an implicit question.
- **questions** — open-ended questions that require research or investigation to answer. The author wants an answer or understanding; the file is phrased as an interrogation.
- **references** — practical artifacts you use directly: a checklist to check off, a log to append to, a procedure to follow, a personal quick-reference card. The value is in using it, not in extracting knowledge from it.
- **inconclusive** — files that cannot be clearly classified, cannot be read, or are equally weighted between two types.

## Process

1. **Determine mode** — check whether an argument was passed. If it looks like a filesystem path, use it as the source directory. If it is direct text, skip to step 5. If no argument, use `raw/inbox/`.
2. **Scan** the source directory for files.
3. **Pre-read check** — before reading each file, check its line count:
   - ≤ 200 lines: read the full file.
   - \> 200 lines: read three windows — first 30 lines, 30 lines from the midpoint, last 30 lines.
4. **Read and learn** — understand the file's purpose and intent. For non-text files (images, PDFs, etc.), attempt to read or interpret using available native tools. If unreadable, move to `inconclusive/` and create a sidecar metadata file (see Handling Unreadable Files).
5. **Classify** — choose the proper type (see Types and Disambiguation).
6. **Move or create** — move the file to `raw/<type>/`. For direct text input, write the content to `raw/<type>/<derived-filename>.md`.
7. **Skip** files already in a target folder (idempotent).
8. **Report** classification and action taken for each file.

## Disambiguation

- **Sources vs. references**: ask "do I learn from this, or do I use it?" Informational content about any topic — no matter the subject — is a source. A practical artifact you act on is a reference. If a file contains both depth (conceptual explanation) and a practical component (e.g., an explainer of a technique that also includes a step-by-step procedure to run), classify as a source — `/callosum:absorb` will extract both the concept knowledge and any practical pages from it.
- **Ideas vs. questions**: if the primary intent is to *get an answer or understanding*, it's a question. If the primary intent is to *build, try, or create something*, it's an idea. If both are equally present, classify as `inconclusive`.
- **When in doubt**: prefer `inconclusive` over a forced classification.

## Handling Unreadable Files

If a file cannot be read or interpreted (unsupported binary format, no tool available for the file type):
1. Move the file to `raw/inconclusive/`.
2. Create a sidecar file `<original_filename>.meta.md` alongside it, containing only the reason classification failed (e.g., `No tool available to read .exe files in this harness`).

## Rules

<HardGate>
1. Never classify a file based on its filename or extension alone. You must read or interpret content first.
2. Never modify the content of any file during classification.
3. Never skip the line count check. Always apply the 3-window sampling strategy for files over 200 lines.
</HardGate>

4. Always create the target type directory if it doesn't exist.
5. Do not perform any action other than reading, moving, or creating files and directories.
