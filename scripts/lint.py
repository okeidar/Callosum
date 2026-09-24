#!/usr/bin/env python3
"""Callosum lint: deterministic contract validation over a whole mind wiki.

Reuses scripts/checks.py — the same single source of truth the prewrite gate enforces — and
adds tree-level diagnostics the gate can't see (link resolution, bidirectionality, staleness,
index drift, library orphans). Contract only: semantic quality belongs to /prune.

    python3 -m scripts.lint <mind-root> [--fix] [--format json|text]

Exit codes: 0 clean (or warnings only), 1 contract violations found, 2 bad invocation.
`--fix` regenerates the hook-maintained index.md from the tree.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts import checks, mind_utils as mu  # noqa: E402

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:\|[^\]]*)?\]\]")
BASIS_LINE_RE = re.compile(r"-\s*\[\[([^\]|]+)\]\]\s*\(last-updated:\s*(\d{4}-\d{2}-\d{2})\)")


def walk_md(root, sub):
    base = os.path.join(root, sub)
    for dirpath, _, files in os.walk(base):
        for name in sorted(files):
            if name.endswith(".md") and name != "AGENTS.md":
                yield os.path.join(dirpath, name)


def load_pages(root):
    pages = {}
    for path in walk_md(root, "wiki"):
        rel = mu.relpath_in_root(path, root)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        fm, _ = mu.parse_frontmatter(content)
        pages[rel] = {"fm": fm or {}, "content": content}
    return pages


def link_registry(pages):
    reg = {}
    for rel, page in pages.items():
        reg[mu.slug_of(rel).lower()] = rel
        title = str(page["fm"].get("title", "")).strip().lower()
        if title:
            reg.setdefault(title, rel)
    return reg


def expected_index(pages):
    lines = []
    for rel in sorted(pages):
        fm = pages[rel]["fm"]
        if not fm.get("title"):
            continue  # free-form data pages without frontmatter are not indexed
        _, body = mu.split_frontmatter(pages[rel]["content"])
        desc = ""
        for line in (body or "").splitlines():
            s = line.strip()
            if s and not s.startswith("#"):
                desc = s[:120]
                break
        lines.append(f"- [{fm.get('title', mu.slug_of(rel))}]({rel}) | {fm.get('type','unknown')} | {fm.get('domain','unknown')} | {desc}")
    return lines


def changed_pages(root, ref=None):
    """Wiki pages (rel paths) changed in git: uncommitted (incl. untracked) or since REF."""
    def git(*argv):
        return subprocess.run(["git", "-C", root, *argv], capture_output=True, text=True)
    names = set()
    if ref:
        r = git("diff", "--name-only", ref, "--")
        if r.returncode != 0:
            return None
        names.update(r.stdout.splitlines())
    else:
        r = git("status", "--porcelain", "--untracked-files=all")
        if r.returncode != 0:
            return None
        for line in r.stdout.splitlines():
            names.add(line[3:].strip().strip('"'))
    return sorted(n for n in names if n.startswith("wiki/") and n.endswith(".md"))


def recent_pages(pages, days):
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    return sorted(rel for rel, p in pages.items()
                  if str(p["fm"].get("last-updated", "")) >= cutoff)


def check_body_links(root, rel, page, reg):
    """Resolve body [[wikilinks]] (governed pages only - data folders stay free-form).
    Path-form links ([[wiki/x.md]]) resolve as files; slug/title links against the page
    registry. The postwrite hook normalizes link FORM; resolution is lint's job (contract
    section 10). Forward references are legal but reported, same as related-pages."""
    declared, _ = checks.load_profile(root, rel)
    if declared == "exempt":
        return []
    reserved_roots = set(mu.RESERVED_TYPE_FOLDERS.values())
    if not any(rel.startswith(r + "/") for r in reserved_roots):
        return []
    _, body = mu.split_frontmatter(page["content"])
    issues = []
    seen = set()
    for m in WIKILINK_RE.finditer(body or ""):
        target = m.group(1).strip()
        if target in seen:
            continue
        seen.add(target)
        if "/" in target:
            if not os.path.exists(os.path.normpath(os.path.join(root, target))):
                issues.append(checks.issue("body_link_unresolved", "warn", rel,
                                           f"body link path does not resolve: [[{target}]]"))
            continue
        t = target.lower()
        if not (reg.get(t) or reg.get(t.replace(" ", "-"))):
            issues.append(checks.issue("body_link_unresolved", "warn", rel,
                                       f"body link does not resolve to a page: [[{target}]]"))
    return issues


def check_books(root):
    """Book TOC <-> book headings agreement (contract section 2): every TOC chapter slug
    must map to a real heading in library/<slug>/book.md."""
    issues = []
    lib_root = os.path.join(root, "library")
    if not os.path.isdir(lib_root):
        return issues
    for dirpath, _, files in os.walk(lib_root):
        if "book.md" not in files:
            continue
        rel_dir = mu.relpath_in_root(dirpath, root)
        toc = mu.book_toc_slugs(os.path.join(dirpath, "index.md"))
        if toc is None:
            issues.append(checks.issue("book_toc_missing", "warn",
                                       os.path.join(rel_dir, "index.md").replace(os.sep, "/"),
                                       "book has no TOC index.md (chapter locators cannot resolve)"))
            continue
        heads = set(mu.book_heading_slugs(os.path.join(dirpath, "book.md")) or [])
        for slug in toc:
            if slug not in heads:
                issues.append(checks.issue("book_toc_mismatch", "warn",
                                           os.path.join(rel_dir, "index.md").replace(os.sep, "/"),
                                           f"TOC chapter slug {slug!r} matches no heading in book.md"))
    return issues


def run(root, fix=False, only=None):
    """Lint a mind root. `only` (a set of wiki/ rel paths) scopes per-page checks to those
    pages; tree-level checks (secrets sweep, library orphans, index drift, book TOCs) are
    global by nature and run only in a full (unscoped) pass."""
    issues = []
    pages = load_pages(root)
    reg = link_registry(pages)

    # per-page contract checks (same code path as the gate)
    for rel, page in pages.items():
        if only is not None and rel not in only:
            continue
        issues += checks.check_wiki_page(root, rel, page["content"])
        issues += check_body_links(root, rel, page, reg)

        fm, content = page["fm"], page["content"]
        if "last-updated" not in fm:
            issues.append(checks.issue("missing_last_updated", "warn", rel,
                                       "no last-updated stamp (postwrite hook did not run?)"))
        # legacy pages: no anchors in a knowledge/derived page
        if checks.family_of(str(fm.get("type", ""))) in ("knowledge", "derived"):
            if not mu.timeline_anchors(content):
                issues.append(checks.issue("legacy_uncited", "info", rel,
                                           "pre-v2 page: Timeline has no ^tN anchors"))
        for m in mu.SOURCE_LINE_RE.finditer(content):
            target = (m.group(1) or m.group(2) or "").strip()
            if target.startswith(("archive/sources/", "wiki/sources/")):
                issues.append(checks.issue("legacy_source_location", "info", rel,
                                           f"cites retired source location: {target}"))

        # link resolution + bidirectionality
        related = fm.get("related-pages") or []
        if isinstance(related, list):
            for item in related:
                mlink = WIKILINK_RE.search(str(item))
                if not mlink:
                    continue
                target = mlink.group(1).strip().lower()
                target_rel = reg.get(target) or reg.get(target.replace(" ", "-"))
                if not target_rel:
                    issues.append(checks.issue("page_link_unresolved", "warn", rel,
                                               f"related-pages link does not resolve: [[{mlink.group(1)}]]"))
                    continue
                back = pages[target_rel]["fm"].get("related-pages") or []
                self_slug = mu.slug_of(rel).lower()
                self_title = str(fm.get("title", "")).lower()
                if not any(self_slug in str(b).lower() or (self_title and self_title in str(b).lower())
                           for b in back):
                    issues.append(checks.issue("related_pages_not_bidirectional", "warn", rel,
                                               f"[[{mlink.group(1)}]] does not link back to this page"))

        # staleness of derived pages
        for entry in (fm.get("derived_from") or []):
            if not isinstance(entry, dict):
                continue
            src, observed = entry.get("page"), str(entry.get("observed", ""))
            cur = pages.get(src, {}).get("fm", {}).get("last-updated", "")
            if src and src not in pages:
                issues.append(checks.issue("derived_from_unresolved", "warn", rel,
                                           f"derived_from page missing: {src}"))
            elif observed and str(cur) > observed:
                issues.append(checks.issue("stale_synthesis", "warn", rel,
                                           f"derived from {src} at {observed}, now {cur}"))

        # stale idea verdicts via Basis
        if fm.get("type") == "idea" and fm.get("verdict"):
            verdict_date = str(fm.get("date", ""))
            for bm in BASIS_LINE_RE.finditer(content):
                target_rel = reg.get(bm.group(1).strip().lower()) or \
                    reg.get(bm.group(1).strip().lower().replace(" ", "-"))
                if not target_rel:
                    continue
                cur = str(pages[target_rel]["fm"].get("last-updated", ""))
                if verdict_date and cur > verdict_date:
                    issues.append(checks.issue("stale_verdict", "warn", rel,
                                               f"basis [[{bm.group(1)}]] updated {cur}, after verdict {verdict_date}"))

    if only is None:
        issues += _run_global_checks(root, pages, fix=fix)
    return issues


def _run_global_checks(root, pages, fix=False):
    issues = []
    # universal checks over every governed zone (same scope as the gate — govern by
    # default, so a secret in raw/ or archive/ is caught here too, not only at write time)
    for sub in ("raw", "archive", "library"):
        base = os.path.join(root, sub)
        if not os.path.isdir(base):
            continue
        for dirpath, _, files in os.walk(base):
            for name in sorted(files):
                if name.startswith(".") or not name.endswith((".md", ".txt", ".json", ".jsonl", ".yaml", ".yml", ".csv")):
                    continue
                p = os.path.join(dirpath, name)
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        text = f.read()
                except (OSError, UnicodeDecodeError):
                    continue
                issues += checks.check_secrets(mu.relpath_in_root(p, root), text)

    issues += check_books(root)

    # library orphans
    all_wiki_text = "\n".join(p["content"] for p in pages.values())
    lib_root = os.path.join(root, "library")
    if os.path.isdir(lib_root):
        for dirpath, _, files in os.walk(lib_root):
            for name in sorted(files):
                if name.startswith(".") or name == "index.md":
                    continue
                rel = mu.relpath_in_root(os.path.join(dirpath, name), root)
                key = rel if name != "book.md" else os.path.dirname(rel)
                if key not in all_wiki_text:
                    issues.append(checks.issue("library_orphan", "info", rel,
                                               "library item not cited by any wiki page (not yet distilled)"))

    # index drift
    index_path = os.path.join(root, "index.md")
    expected = expected_index(pages)
    actual = []
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            actual = [l.rstrip("\n") for l in f if l.strip().startswith("- [")]
    if sorted(actual) != sorted(expected):
        issues.append(checks.issue("index_drift", "warn", "index.md",
                                   f"index has {len(actual)} entries, tree has {len(expected)} (fixable)"))
        if fix:
            with open(index_path, "w", encoding="utf-8") as f:
                f.write("# Mind Wiki Index\n\n" + "\n".join(expected) + "\n")
            issues.append(checks.issue("index_rebuilt", "info", "index.md", "index.md regenerated by --fix"))

    return issues


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", help="mind root to lint")
    ap.add_argument("--fix", action="store_true", help="regenerate hook-maintained artifacts")
    ap.add_argument("--format", choices=["json", "text"], default="text")
    ap.add_argument("--changed", nargs="?", const="", metavar="REF",
                    help="scope to wiki pages changed in git (uncommitted, or since REF)")
    ap.add_argument("--recent", type=int, metavar="DAYS", default=None,
                    help="scope to wiki pages whose last-updated is within DAYS days")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    if not os.path.exists(os.path.join(root, ".callosum")):
        print(f"not a mind root (no .callosum marker): {root}", file=sys.stderr)
        return 2

    only = None
    scope_desc = "full"
    if args.changed is not None:
        changed = changed_pages(root, ref=args.changed or None)
        if changed is None:
            print("lint --changed needs the mind root to be a git repository", file=sys.stderr)
            return 2
        only = set(changed)
        scope_desc = f"changed ({args.changed or 'uncommitted'}): {len(only)} page(s)"
    if args.recent is not None:
        recent = set(recent_pages(load_pages(root), args.recent))
        only = recent if only is None else (only | recent)
        scope_desc = f"recent ({args.recent}d): {len(recent)} page(s)" if args.changed is None \
            else scope_desc + f" + recent: {len(recent)} page(s)"

    issues = run(root, fix=args.fix, only=only)
    errors = [i for i in issues if i["severity"] == "block"]
    if args.format == "json":
        print(json.dumps({"root": root, "scope": scope_desc, "issues": issues,
                          "summary": {"errors": len(errors),
                                      "warnings": len([i for i in issues if i['severity'] == 'warn']),
                                      "info": len([i for i in issues if i['severity'] == 'info'])}},
                         indent=2))
    else:
        print(f"scope: {scope_desc}")
        for i in issues:
            print(f"{i['severity'].upper():5} {i['kind']:32} {i['path']}: {i['message']}")
        print(f"\n{len(errors)} error(s), "
              f"{len([i for i in issues if i['severity'] == 'warn'])} warning(s), "
              f"{len([i for i in issues if i['severity'] == 'info'])} info")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

