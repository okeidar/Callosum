"""The single source of truth for what a *valid* mind-wiki write is.

The prewrite gate (hooks/prewrite_gate.py) calls `check_write` and blocks on any issue with
severity == "block". The linter (scripts/lint.py) reuses the same checks post-hoc and adds
tree-level diagnostics. Keep every rule here deterministic — judgment belongs to skills.

Rules are defined by template/wiki-contract.md. If this file and the contract disagree, fix
one of them — never fork the logic elsewhere.
"""
from __future__ import annotations

import os
import re

from . import mind_utils as mu


def issue(kind, severity, path, message, line=None):
    d = {"kind": kind, "severity": severity, "path": path, "message": message}
    if line is not None:
        d["line"] = line
    return d


REQUIRED_BASE = ["title", "type", "domain", "tags", "synthesized"]
REQUIRED_BY_FAMILY = {
    "knowledge": ["sources", "related-pages"],
    "derived": ["sources", "related-pages"],
    "idea": ["verdict", "date"],
    # collection pages are DATA, not knowledge: `sources` is provenance when a library
    # original exists, but a hand-written data page has none — never require it
    "collection": [],
}
VALID_VERDICTS = {"RIPENED", "REJECTED", "CONDITIONAL"}


def family_of(page_type: str):
    if page_type in mu.KNOWLEDGE_TYPES:
        return "knowledge"
    if page_type in mu.DERIVED_TYPES:
        return "derived"
    if page_type == "idea":
        return "idea"
    return "collection"


# ---------------------------------------------------------------------------
# Governance resolver (shared scope decider — the gate and lint both use THIS,
# never their own path logic; see wiki-contract.md §11)
# ---------------------------------------------------------------------------

PROFILE_FILE = ".callosum-profile"
VALID_PROFILES = {"knowledge", "data", "collection", "idea", "exempt"}  # collection = data alias
_profile_cache = {}


def load_profile(mind_root: str, rel_path: str):
    """Nearest .callosum-profile declaration on the path from the file's folder up to wiki/.
    Returns (profile_or_None, disabled_kinds_set). No declaration → defaults by page type."""
    folder = os.path.normpath(os.path.dirname(os.path.join(mind_root, rel_path)))
    wiki_top = os.path.normpath(os.path.join(mind_root, "wiki"))
    visited = []
    result = (None, set())
    probe = folder
    while True:
        if probe in _profile_cache:
            result = _profile_cache[probe]
            break
        visited.append(probe)
        decl = os.path.join(probe, PROFILE_FILE)
        if os.path.exists(decl):
            try:
                with open(decl, "r", encoding="utf-8") as f:
                    data = mu._parse_subset(f.read())
            except OSError:
                data = {}
            profile = data.get("profile")
            if profile not in VALID_PROFILES:
                profile = None
            result = (profile, set(data.get("disable") or []))
            break
        if probe == wiki_top or os.path.dirname(probe) == probe:
            break
        probe = os.path.dirname(probe)
    for v in visited:
        _profile_cache[v] = result
    return result


UNIVERSAL_KINDS = {"secret_material"}  # never disableable — apply to every governed file


def apply_governance(issues, disabled):
    if not disabled:
        return issues
    return [i for i in issues if i["kind"] in UNIVERSAL_KINDS or i["kind"] not in disabled]


def zone_of(rel_path: str):
    if rel_path in ("index.md", "log.md"):
        return "generated"
    first = rel_path.split("/", 1)[0]
    if first == "wiki":
        return "wiki"
    if first == "library":
        return "library"
    if first == "raw":
        return "raw"
    if first == "archive":
        return "archive"
    return "meta"


# ---------------------------------------------------------------------------
# Content checks (shared by gate and lint)
# ---------------------------------------------------------------------------

def check_secrets(rel_path, content):
    issues = []
    for pat in mu.SECRET_PATTERNS:
        m = pat.search(content)
        if m:
            issues.append(issue(
                "secret_material", "block", rel_path,
                f"content matches secret pattern {pat.pattern[:40]!r} — credentials must never land in the wiki",
            ))
    return issues


def check_wiki_page(mind_root, rel_path, content, old_content=None):
    """Full contract checks for a page under wiki/. Scope and strictness come from the
    governance resolver: a folder's .callosum-profile can exempt it, re-profile it, or
    disable named checks — extensions register areas this way instead of patching here."""
    if not rel_path.endswith(".md"):
        return []
    declared, disabled = load_profile(mind_root, rel_path)
    if declared == "exempt":
        return check_secrets(rel_path, content)  # universal checks never opt out

    # arbitrary-data folders: anything under wiki/ OUTSIDE the reserved type folders is
    # free-form data (whatever domains emerge from the content) — the contract's structure
    # rules do not apply there. Universal checks + a gentle plugin-consumability nudge only.
    reserved_roots = set(mu.RESERVED_TYPE_FOLDERS.values())
    in_reserved = any(rel_path.startswith(r + "/") for r in reserved_roots)
    if not in_reserved and declared in (None, "data", "collection"):
        issues = check_secrets(rel_path, content)
        fm, _ = mu.parse_frontmatter(content)
        if fm is None or "title" not in fm or "type" not in fm:
            issues.append(issue(
                "data_page_frontmatter_recommended", "info", rel_path,
                "free-form data page; adding title/type/domain/tags frontmatter makes it "
                "consumable by plugins",
            ))
        return apply_governance(issues, disabled)

    issues = []
    fm, err = mu.parse_frontmatter(content)
    if fm is None:
        return apply_governance(
            [issue("frontmatter_invalid", "block", rel_path, err or "frontmatter missing")], disabled)

    page_type = fm.get("type")
    if not isinstance(page_type, str) or not page_type:
        return apply_governance(
            [issue("type_missing", "block", rel_path, "frontmatter has no `type`")], disabled)

    # required fields — a declared profile overrides the type-derived family
    fam = declared if declared in ("knowledge", "idea") else family_of(page_type)
    for field in REQUIRED_BASE + REQUIRED_BY_FAMILY[fam]:
        if field not in fm or fm.get(field) in (None, ""):
            issues.append(issue(
                "frontmatter_field_missing", "block", rel_path,
                f"required frontmatter field `{field}` missing for type `{page_type}`",
            ))

    # type <-> folder agreement (a declared profile owns its folder's placement rules)
    expected = mu.RESERVED_TYPE_FOLDERS.get(page_type) if declared is None else None
    if expected:
        if not rel_path.startswith(expected + "/"):
            issues.append(issue(
                "type_folder_mismatch", "block", rel_path,
                f"type `{page_type}` must live under {expected}/",
            ))
        elif page_type != "idea":
            # categorical subdir: wiki/<type>/<category>/<slug>.md
            depth = rel_path.count("/")
            if depth < 3:
                issues.append(issue(
                    "missing_category_subdir", "block", rel_path,
                    f"pages under {expected}/ use a category subdir: {expected}/<category>/<slug>.md",
                ))
    elif declared is None:
        # collection type: must be under wiki/ but not inside a reserved type folder
        reserved_roots = set(v for v in mu.RESERVED_TYPE_FOLDERS.values())
        if any(rel_path.startswith(r + "/") for r in reserved_roots):
            issues.append(issue(
                "type_folder_mismatch", "block", rel_path,
                f"collection type `{page_type}` must live in its own wiki/<domain>/ folder, "
                f"not a reserved type folder",
            ))

    if fam == "idea":
        verdict = str(fm.get("verdict", "")).strip()
        if verdict and verdict not in VALID_VERDICTS:
            issues.append(issue(
                "verdict_invalid", "block", rel_path,
                f"verdict `{verdict}` not in {sorted(VALID_VERDICTS)}",
            ))
        return apply_governance(issues + check_secrets(rel_path, content), disabled)

    if fam == "collection":
        return apply_governance(issues + check_secrets(rel_path, content), disabled)

    # knowledge / derived pages: section structure
    _, body = mu.split_frontmatter(content)
    sections = mu.find_sections(body)
    ct_span = sections.get("compiled truth")
    tl_span = sections.get("timeline")
    if ct_span is None or tl_span is None:
        issues.append(issue(
            "sections_missing", "block", rel_path,
            "knowledge/derived pages need `## Compiled Truth` followed by `## Timeline`",
        ))
        return apply_governance(issues + check_secrets(rel_path, content), disabled)
    if ct_span[0] > tl_span[0]:
        issues.append(issue(
            "sections_out_of_order", "block", rel_path,
            "`## Compiled Truth` must come before `## Timeline`",
        ))

    tl_text = mu.section_text(body, sections, "timeline") or ""
    anchors = mu.timeline_anchors(tl_text)
    anchored = bool(anchors)

    # v2 rules apply to anchored pages only (legacy pages: lint reports info)
    if anchored:
        issues += _check_v2_citations(rel_path, body, sections, anchors)
        issues += _check_timeline_sources(mind_root, rel_path, tl_text)

    # append-only timeline: anchors present before the edit must survive it
    if old_content is not None:
        old_anchors = mu.timeline_anchors(old_content)
        removed = old_anchors - mu.timeline_anchors(content)
        if removed:
            issues.append(issue(
                "timeline_anchor_removed", "block", rel_path,
                f"Timeline is append-only: anchors removed by this edit: "
                f"{', '.join('^t%d' % n for n in sorted(removed))}",
            ))

    return apply_governance(issues + check_secrets(rel_path, content), disabled)


def _check_v2_citations(rel_path, body, sections, anchors):
    issues = []
    ct_text = mu.section_text(body, sections, "compiled truth") or ""
    for offset, line in enumerate(ct_text.splitlines()):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        cits = mu.CITATION_RE.findall(stripped)
        cited_nums = set(int(re.search(r"\d+", c).group()) for c in cits)
        if not cits:
            issues.append(issue(
                "claim_uncited", "block", rel_path,
                f"Compiled Truth claim has no [[#^tN]] citation: {stripped[:80]!r}",
            ))
            continue
        dangling = cited_nums - anchors
        if dangling:
            issues.append(issue(
                "citation_unresolved", "block", rel_path,
                f"claim cites missing anchor(s) {sorted('^t%d' % n for n in dangling)}: {stripped[:60]!r}",
            ))
        if "[CONTESTED]" in stripped and len(cits) < 2:
            issues.append(issue(
                "contested_single_cited", "block", rel_path,
                f"[CONTESTED] claims must cite both sides (≥2 anchors): {stripped[:60]!r}",
            ))
    return issues


def _check_timeline_sources(mind_root, rel_path, tl_text):
    issues = []
    lines = tl_text.splitlines()
    for idx, line in enumerate(lines):
        m = mu.SOURCE_LINE_RE.match(line.strip())
        if not m:
            continue
        target = (m.group(1) or m.group(2)).strip()
        if target.startswith("http://") or target.startswith("https://"):
            continue
        root_real = os.path.realpath(mind_root)
        abs_target = os.path.realpath(os.path.join(root_real, target))
        try:
            inside_root = os.path.commonpath((root_real, abs_target)) == root_real
        except ValueError:  # different drives on Windows
            inside_root = False
        if not inside_root:
            issues.append(issue(
                "source_path_escapes_root", "block", rel_path,
                f"Source path escapes the mind root: {target}",
            ))
            continue
        if not os.path.exists(abs_target):
            issues.append(issue(
                "source_path_unresolved", "block", rel_path,
                f"Timeline Source does not resolve: {target}",
            ))
            continue
        # a Locator: line may follow the Source: line within the same entry
        locator = None
        for nxt in lines[idx + 1:]:
            stripped = nxt.strip()
            if not stripped:
                continue
            lm = mu.LOCATOR_LINE_RE.match(stripped)
            if lm:
                locator = lm.group(1)
            break
        if locator:
            issues += _check_locator(mind_root, rel_path, target, abs_target, locator)
    return issues


def _check_locator(mind_root, rel_path, target, abs_target, locator):
    """Validate a Timeline Locator against the actual source file (wiki-contract.md section 4):
    line spans (L10-40) against the file's line count; chapter slugs against the book's TOC."""
    span = mu.LINE_SPAN_RE.match(locator)
    if span:
        start, end = (int(span.group(1)), int(span.group(2)))
        total = mu.count_lines(abs_target)
        if start < 1 or end < start:
            return [issue(
                "locator_span_invalid", "block", rel_path,
                f"Locator {locator} must be an ordered, one-based line span (for example L10-40)",
            )]
        if total is not None and end > total:
            return [issue(
                "locator_span_out_of_range", "block", rel_path,
                f"Locator {locator} exceeds {target} length ({total} lines)",
            )]
        return []
    # chapter form: only meaningful for a book source (library/<slug>/book.md)
    norm = target.replace("\\", "/")
    if not norm.startswith("library/") or os.path.basename(norm) != "book.md":
        return [issue(
            "locator_unknown_chapter", "block", rel_path,
            f"Locator {locator!r} names a chapter but {target} is not a book "
            f"(books live at library/<slug>/book.md; use a line span like L10-40 for flat sources)",
        )]
    toc = mu.book_toc_slugs(os.path.join(os.path.dirname(abs_target), "index.md"))
    if toc is None:
        return [issue(
            "locator_unknown_chapter", "block", rel_path,
            f"Locator {locator!r} but the book has no TOC at {os.path.dirname(target)}/index.md",
        )]
    if locator not in toc:
        return [issue(
            "locator_unknown_chapter", "block", rel_path,
            f"Locator {locator!r} is not in the book's TOC (have: {', '.join(toc) or 'none'})",
        )]
    return []


# ---------------------------------------------------------------------------
# Write-time entry point (the gate's single call)
# ---------------------------------------------------------------------------

def check_write(mind_root, file_path, new_content, tool_name="Write"):
    """All write-time checks for a single file. Returns a list of issues;
    the gate blocks when any has severity == 'block'."""
    rel = mu.relpath_in_root(file_path, mind_root)
    zone = zone_of(rel)
    exists = os.path.exists(file_path)
    old_content = None
    if exists:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                old_content = f.read()
        except (OSError, UnicodeDecodeError):
            old_content = None

    if zone == "generated":
        return [issue(
            "generated_artifact_write", "block", rel,
            f"{rel} is hook-maintained — never write it directly (lint --fix regenerates it)",
        )]

    if zone == "library":
        if exists:
            return [issue(
                "library_immutable", "block", rel,
                "library items are write-once: nothing in library/ is ever edited after capture",
            )]
        return check_secrets(rel, new_content)

    if zone == "wiki":
        if rel.startswith("wiki/ideas/") and exists and rel.endswith(".md"):
            fm_old, _ = mu.parse_frontmatter(old_content or "")
            if (fm_old or {}).get("type") == "idea" and \
                    os.environ.get("CALLOSUM_ALLOW_IDEA_WRITE") != "1":
                return [issue(
                    "idea_page_autonomy", "block", rel,
                    "existing idea pages are not modified unilaterally — propose the change "
                    "to the user; /incubate and human-approved /adapt set "
                    "CALLOSUM_ALLOW_IDEA_WRITE=1",
                )]
        return check_wiki_page(mind_root, rel, new_content, old_content)

    # a "meta" path containing a mind-structure component means the agent doubled the
    # root (e.g. cwd inside the mind + a path still prefixed with the mind dir name)
    if zone == "meta":
        parts = rel.split("/")[:-1]
        if any(p in ("wiki", "raw", "library", "archive") for p in parts):
            return [issue(
                "nested_mind_write", "block", rel,
                f"path resolves outside the mind's zones but contains a mind folder "
                f"({rel}) — you likely doubled the root; write relative to the mind root "
                f"or use an absolute path",
            )]

    # raw/, archive/, remaining meta files: only the secrets rail applies
    return check_secrets(rel, new_content)

