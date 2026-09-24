"""Shared parsing and resolution utilities for the Callosum deterministic layer.

No third-party dependencies: hooks must run in any Python 3.9+ environment. PyYAML is used
when available, with a subset parser fallback that covers the contract's frontmatter shapes.
"""
from __future__ import annotations

import os
import re
from datetime import date

RESERVED_TYPE_FOLDERS = {
    "entity": "wiki/entities",
    "concept": "wiki/concepts",
    "principle": "wiki/concepts",
    "research": "wiki/research",
    "synthesis": "wiki/synthesis",
    "idea": "wiki/ideas",
}
KNOWLEDGE_TYPES = {"entity", "concept", "principle"}
DERIVED_TYPES = {"research", "synthesis"}

# block anchors only — `[[#^tN]]` citations are excluded by the lookbehind
ANCHOR_RE = re.compile(r"(?<!\[\[#)\^t(\d+)\b")
CITATION_RE = re.compile(r"\[\[#\^t\d+\]\]")
TIMELINE_HEADING_RE = re.compile(r"^###\s+\[(\d{4}-\d{2}-\d{2})\]")
SOURCE_LINE_RE = re.compile(r"^Source:\s*(?:\[[^\]]*\]\(([^)]+)\)|(\S+))\s*$")
LOCATOR_LINE_RE = re.compile(r"^Locator:\s*(\S+)\s*$")
LINE_SPAN_RE = re.compile(r"^L(\d+)-(\d+)$")
# book TOC line: `- <chapter-slug>: <chapter title>` (see wiki-contract.md section 2)
TOC_ENTRY_RE = re.compile(r"^-\s*([a-z0-9][a-z0-9-]*)\s*:\s+(.+?)\s*$")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$")
INLINE_PATH_LINK_RE = re.compile(r"\[\[((?:wiki|library|archive|raw)/[^\]|#]+?)(\|[^\]]+)?\]\]")

SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bghp_[A-Za-z0-9]{36}\b"),
    re.compile(r"\bxox[bap]-[A-Za-z0-9-]{10,}"),
    re.compile(r"""(?i)\b(api[_-]?key|secret|token|password)\b\s*[:=]\s*['"]?[A-Za-z0-9_\-/+]{20,}"""),
]


def find_mind_root(path: str):
    """Walk up from path to the nearest directory containing a .callosum marker."""
    cur = os.path.abspath(path)
    if os.path.isfile(cur):
        cur = os.path.dirname(cur)
    while True:
        if os.path.exists(os.path.join(cur, ".callosum")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def resolve_default_mind_root():
    env = os.environ.get("CALLOSUM_MIND_ROOT")
    if env and os.path.isdir(env):
        return os.path.abspath(env)
    here = find_mind_root(os.getcwd())
    if here:
        return here
    default = os.path.expanduser("~/mind")
    if os.path.exists(os.path.join(default, ".callosum")):
        return default
    return None


# ---------------------------------------------------------------------------
# Frontmatter
# ---------------------------------------------------------------------------

def split_frontmatter(content: str):
    """Return (frontmatter_text, body) or (None, content) when absent."""
    if not content.startswith("---"):
        return None, content
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", content, re.DOTALL)
    if not m:
        return None, content
    return m.group(1), m.group(2)


def _parse_scalar(val: str):
    val = val.strip()
    if val.startswith('"') and val.endswith('"') and len(val) >= 2:
        return val[1:-1]
    if val.startswith("'") and val.endswith("'") and len(val) >= 2:
        return val[1:-1]
    if val == "true":
        return True
    if val == "false":
        return False
    return val


def _parse_subset(text: str):
    """Parse the YAML subset used by the contract: scalars, inline lists,
    block lists of scalars, and block lists of one-level dicts (derived_from)."""
    data = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key, rest = m.group(1), m.group(2).strip()
        if rest.startswith("[") and rest.endswith("]"):
            inner = rest[1:-1].strip()
            data[key] = [] if not inner else [_parse_scalar(v) for v in inner.split(",")]
            i += 1
            continue
        if rest:
            data[key] = _parse_scalar(rest)
            i += 1
            continue
        # block value: list of scalars or list of dicts
        items = []
        i += 1
        current_dict = None
        while i < len(lines):
            nxt = lines[i]
            if not nxt.strip():
                i += 1
                continue
            lm = re.match(r"^\s+-\s*(.*)$", nxt)
            km = re.match(r"^\s+([A-Za-z0-9_-]+):\s*(.*)$", nxt)
            if lm:
                val = lm.group(1).strip()
                dm = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", val)
                if dm:
                    current_dict = {dm.group(1): _parse_scalar(dm.group(2))}
                    items.append(current_dict)
                else:
                    current_dict = None
                    items.append(_parse_scalar(val))
                i += 1
            elif km and current_dict is not None:
                current_dict[km.group(1)] = _parse_scalar(km.group(2))
                i += 1
            else:
                break
        data[key] = items
    return data


def parse_frontmatter(content: str):
    """Return (dict_or_None, error_or_None). None dict means no/unparseable frontmatter."""
    fm_text, _ = split_frontmatter(content)
    if fm_text is None:
        return None, "missing or malformed frontmatter block"
    try:
        import yaml  # type: ignore
        try:
            data = yaml.safe_load(fm_text)
        except Exception as exc:
            return None, f"frontmatter does not parse as YAML: {exc}"
        if not isinstance(data, dict):
            return None, "frontmatter is not a mapping"
        return data, None
    except ImportError:
        return _parse_subset(fm_text), None


# ---------------------------------------------------------------------------
# Page model
# ---------------------------------------------------------------------------

def find_sections(body: str):
    """Return {section_title_lower: (start_line, end_line)} for '## ' headings."""
    sections = {}
    lines = body.splitlines()
    current, start = None, 0
    for idx, line in enumerate(lines):
        if line.startswith("## "):
            if current is not None:
                sections[current] = (start, idx)
            current = line[3:].strip().lower()
            start = idx + 1
    if current is not None:
        sections[current] = (start, len(lines))
    return sections


def section_text(body: str, sections, name: str):
    span = sections.get(name)
    if not span:
        return None
    return "\n".join(body.splitlines()[span[0]:span[1]])


def timeline_anchors(content: str):
    """All ^tN anchors that appear as block anchors in the content."""
    return set(int(n) for n in ANCHOR_RE.findall(content))


def slugify_heading(title: str):
    """GitHub-style heading slug: lowercase, spaces to dashes, strip other punctuation."""
    s = title.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    return re.sub(r"[\s_]+", "-", s).strip("-")


def book_toc_slugs(index_path: str):
    """Chapter slugs declared by a book's TOC (`library/<slug>/index.md`)."""
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return None
    return [m.group(1) for m in (TOC_ENTRY_RE.match(l) for l in text.splitlines()) if m]


def book_heading_slugs(book_path: str):
    """Slugs of every markdown heading in a book file."""
    try:
        with open(book_path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return None
    return [slugify_heading(m.group(1)) for m in
            (HEADING_RE.match(l) for l in text.splitlines()) if m]


def count_lines(path: str):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return sum(1 for _ in f)
    except OSError:
        return None


def relpath_in_root(file_path: str, mind_root: str):
    rel = os.path.relpath(os.path.abspath(file_path), mind_root)
    return rel.replace(os.sep, "/")


def today():
    return date.today().isoformat()


def slug_of(file_path: str):
    return os.path.splitext(os.path.basename(file_path))[0]

