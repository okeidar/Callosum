#!/usr/bin/env python3
"""Idea Board — an example Callosum plugin UI.

A kanban over the idea pipeline's derived pages: columns are verdict states
(RIPENED / CONDITIONAL / REJECTED), each card shows its verdict date and a STALE badge when
any `### Basis` page was updated after the verdict was rendered — the signal to re-run
`/callosum:incubate`. Read-only over `wiki/ideas/` (and page `last-updated` stamps for staleness);
never touches `raw/` or `library/`.

    python3 examples/idea-board-ui/serve.py [mind-root] [--port 8766]

Stdlib only — no dependencies.
"""
import argparse
import http.server
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
from scripts import mind_utils as mu  # noqa: E402

BASIS_LINE_RE = re.compile(r"-\s*\[\[([^\]|]+)\]\]\s*\(last-updated:\s*(\d{4}-\d{2}-\d{2})\)")


def page_registry(mind_root):
    """slug/title (lowercase) -> current last-updated, across all wiki pages."""
    reg = {}
    wiki = os.path.join(mind_root, "wiki")
    for dirpath, _, files in os.walk(wiki):
        for name in files:
            if not name.endswith(".md") or name == "AGENTS.md":
                continue
            try:
                with open(os.path.join(dirpath, name), "r", encoding="utf-8") as f:
                    fm, _ = mu.parse_frontmatter(f.read())
            except OSError:
                continue
            updated = str((fm or {}).get("last-updated", ""))
            reg[mu.slug_of(name).lower()] = updated
            title = str((fm or {}).get("title", "")).strip().lower()
            if title:
                reg.setdefault(title, updated)
    return reg


def load_ideas(mind_root):
    ideas = []
    reg = page_registry(mind_root)
    base = os.path.join(mind_root, "wiki", "ideas")
    if not os.path.isdir(base):
        return ideas
    candidates = []
    for entry in sorted(os.listdir(base)):
        full = os.path.join(base, entry)
        if entry in ("conditional", "rejected"):
            candidates += [os.path.join(full, f) for f in sorted(os.listdir(full))
                           if f.endswith(".md") and f != "AGENTS.md"]
        elif os.path.isdir(full):  # ripened idea subdir
            candidates += [os.path.join(full, f) for f in sorted(os.listdir(full))
                           if f.endswith(".md")]
    for path in candidates:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        fm, _ = mu.parse_frontmatter(content)
        fm = fm or {}
        if fm.get("type") != "idea":
            continue
        verdict = str(fm.get("verdict", "")).upper()
        vdate = str(fm.get("date", ""))
        _, body = mu.split_frontmatter(content)
        stale_because = []
        for m in BASIS_LINE_RE.finditer(body):
            cur = reg.get(m.group(1).strip().lower()) or \
                reg.get(m.group(1).strip().lower().replace(" ", "-")) or ""
            if vdate and cur and cur > vdate:
                stale_because.append(f"{m.group(1)} updated {cur}")
        ideas.append({
            "slug": mu.slug_of(path),
            "title": fm.get("title", mu.slug_of(path)),
            "verdict": verdict if verdict in ("RIPENED", "CONDITIONAL", "REJECTED") else "RIPENED",
            "date": vdate,
            "tags": fm.get("tags") or [],
            "stale": bool(stale_because),
            "stale_because": stale_because,
            "body": body,
            "path": mu.relpath_in_root(path, mind_root),
        })
    return ideas


PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Idea Board</title>
<style>
:root { color-scheme: light dark; font-family: -apple-system, system-ui, sans-serif; }
body { margin: 0 auto; max-width: 1100px; padding: 1.5rem; line-height: 1.45; }
h1 { font-size: 1.4rem; } small { opacity: .6; }
#board { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; align-items: start; }
.col h2 { font-size: .95rem; text-transform: uppercase; letter-spacing: .06em; opacity: .7; }
.card { border: 1px solid color-mix(in srgb, currentColor 15%, transparent);
        border-radius: 10px; padding: .7rem .9rem; margin-bottom: .7rem; cursor: pointer; }
.card:hover { border-color: color-mix(in srgb, currentColor 40%, transparent); }
.card h3 { margin: 0 0 .25rem; font-size: 1rem; }
.badge { display: inline-block; font-size: .7rem; font-weight: 700; padding: .1rem .5rem;
         border-radius: 99px; background: #c2410c22; color: #c2410c; }
@media (prefers-color-scheme: dark) { .badge { color: #fdba74; } }
.tag { display: inline-block; font-size: .72rem; padding: .03rem .45rem; border-radius: 99px;
       background: color-mix(in srgb, currentColor 12%, transparent); margin-right: .25rem; }
#detail { white-space: pre-wrap; }
a { color: inherit; }
@media (max-width: 800px) { #board { grid-template-columns: 1fr; } }
</style></head><body>
<h1>Idea Board <small>— a Callosum plugin (data: wiki/ideas/)</small></h1>
<div id="board-view"><div id="board"></div></div>
<div id="detail-view" style="display:none">
  <p><a href="#" onclick="back();return false">&larr; board</a></p>
  <div id="detail"></div>
</div>
<script>
let IDEAS = [];
const COLS = ['RIPENED', 'CONDITIONAL', 'REJECTED'];
function render() {
  document.getElementById('board').innerHTML = COLS.map(col => {
    const cards = IDEAS.filter(i => i.verdict === col);
    return `<div class="col"><h2>${col} (${cards.length})</h2>` + cards.map(i => `
      <div class="card" onclick="show('${i.slug}')">
        <h3>${i.title} ${i.stale ? '<span class="badge" title="' + i.stale_because.join('; ') + '">STALE</span>' : ''}</h3>
        <div><small>${i.date}</small></div>
        <div>${(i.tags || []).map(t => `<span class="tag">${t}</span>`).join('')}</div>
        <small>${i.path}</small>
      </div>`).join('') + '</div>';
  }).join('');
  if (!IDEAS.length) document.getElementById('board').innerHTML =
    '<p>No idea pages yet — put raw ideas in raw/ideas/ and run /callosum:incubate.</p>';
}
function show(slug) {
  const i = IDEAS.find(x => x.slug === slug);
  document.getElementById('detail').textContent =
    (i.stale ? 'STALE — ' + i.stale_because.join('; ') + '\\n\\n' : '') + i.body;
  document.getElementById('board-view').style.display = 'none';
  document.getElementById('detail-view').style.display = 'block';
}
function back() {
  document.getElementById('detail-view').style.display = 'none';
  document.getElementById('board-view').style.display = 'block';
}
fetch('/api/ideas').then(r => r.json()).then(d => { IDEAS = d; render(); });
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", nargs="?", default=None)
    ap.add_argument("--port", type=int, default=8766)
    args = ap.parse_args()
    mind_root = os.path.abspath(args.root) if args.root else mu.resolve_default_mind_root()
    if not mind_root or not os.path.exists(os.path.join(mind_root, ".callosum")):
        print("no mind root found — pass one explicitly", file=sys.stderr)
        return 1

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/api/ideas"):
                payload = json.dumps(load_ideas(mind_root)).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
            else:
                payload = PAGE.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *a):
            pass

    print(f"Idea Board on http://localhost:{args.port}  (data: {mind_root}/wiki/ideas/)")
    http.server.HTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    sys.exit(main())
