#!/usr/bin/env python3
"""Export a browsable, offline snapshot of a Callosum mind.

Writes ``index.html`` and ``data.json`` to ``<mind>/ui`` by default. The export reads
only wiki pages and omits pages tagged ``sensitive`` or ``private``. It never copies library
contents. Re-run after mind changes; output is deterministic apart from source file updates.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts import mind_utils as mu  # noqa: E402

EXCLUDED_TAGS = {"sensitive", "private"}


def export_data(root):
    pages = []
    root = os.path.realpath(root)
    wiki = os.path.join(root, "wiki")
    if os.path.islink(wiki) or not os.path.isdir(wiki):
        return {"pages": []}
    for dirpath, dirs, files in os.walk(wiki, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not os.path.islink(os.path.join(dirpath, d)))
        for name in sorted(files):
            if not name.endswith(".md") or name == "AGENTS.md":
                continue
            path = os.path.join(dirpath, name)
            if os.path.islink(path):
                continue
            try:
                if os.path.commonpath((os.path.realpath(path), wiki)) != wiki:
                    continue
            except ValueError:
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            except (OSError, UnicodeDecodeError):
                continue
            fm, _ = mu.parse_frontmatter(content)
            if not fm:
                continue
            tags = fm.get("tags") or []
            if not isinstance(tags, list):
                tags = [tags]
            if {str(t).strip().lower() for t in tags} & EXCLUDED_TAGS:
                continue
            _, body = mu.split_frontmatter(content)
            sections = mu.find_sections(body or "")
            compiled = mu.section_text(body or "", sections, "compiled truth")
            timeline = mu.section_text(body or "", sections, "timeline")
            # Data pages are intentionally free-form and need not use the knowledge-page
            # Compiled Truth / Timeline structure. Keep them browsable instead of exporting
            # an empty page. Anchored knowledge pages retain their structured projection.
            if compiled is None:
                compiled = (body or "").strip()
            timeline = timeline or ""
            pages.append({
                "slug": mu.slug_of(path),
                "title": str(fm.get("title") or mu.slug_of(path)),
                "type": str(fm.get("type") or ""),
                "domain": str(fm.get("domain") or ""),
                "tags": tags,
                "path": mu.relpath_in_root(path, root),
                "compiled_truth": compiled.strip(),
                "timeline": timeline.strip(),
            })
    pages.sort(key=lambda p: (p["domain"].lower(), p["title"].lower(), p["path"]))
    return {"pages": pages}


HTML = '''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Callosum Mind</title><style>body{font:16px system-ui;max-width:1100px;margin:auto;padding:2rem}input{width:100%;padding:.7rem}main{display:grid;grid-template-columns:18rem 1fr;gap:2rem}button{display:block;border:0;background:none;text-align:left;padding:.35rem;width:100%;cursor:pointer}pre{white-space:pre-wrap;font:inherit}@media(max-width:700px){main{grid-template-columns:1fr}}</style>
<h1>Callosum Mind</h1><input id="q" placeholder="Search pages"><main><nav id="nav"></nav><article id="page"></article></main>
<script>let P=[];const e=s=>String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));function show(i){let p=P[i];page.innerHTML=`<h2>${e(p.title)}</h2><small>${e(p.domain)} · ${e(p.type)} · ${e(p.path)}</small><h3>Compiled Truth</h3><pre>${e(p.compiled_truth)}</pre><h3>Evidence Timeline</h3><pre>${e(p.timeline)}</pre>`}function draw(){let x=q.value.toLowerCase();nav.innerHTML=P.map((p,i)=>({p,i})).filter(x=>!x||JSON.stringify(x.p).toLowerCase().includes(x)).map(x=>`<button onclick="show(${x.i})">${e(x.p.title)}</button>`).join('')}q.oninput=draw;fetch('data.json').then(r=>r.json()).then(d=>{P=d.pages||[];draw();if(P.length)show(0)})</script>'''


def _prepare_output(output):
    """Create a real output directory without following a final symlink."""
    if os.path.lexists(output):
        if os.path.islink(output) or not os.path.isdir(output):
            raise ValueError(f"unsafe export output: {output}")
    else:
        os.makedirs(output)
    return os.path.realpath(output)


def _atomic_write(path, text):
    """Replace a generated file atomically instead of following a child symlink."""
    fd, temporary = tempfile.mkstemp(prefix=".callosum-export-", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def write_export(root, output):
    output = _prepare_output(output)
    data = export_data(root)
    rendered = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    _atomic_write(os.path.join(output, "data.json"), rendered)
    _atomic_write(os.path.join(output, "index.html"), HTML)
    return len(data["pages"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", nargs="?", default=None)
    ap.add_argument("--output", default=None)
    args = ap.parse_args(argv)
    root = os.path.abspath(args.root) if args.root else mu.resolve_default_mind_root()
    if not root or not os.path.exists(os.path.join(root, ".callosum")):
        print("no mind root found - pass one explicitly", file=sys.stderr)
        return 1
    output = os.path.abspath(args.output) if args.output else os.path.join(root, "ui")
    count = write_export(root, output)
    print(f"exported {count} page(s) to {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
