#!/usr/bin/env python3
"""Recipe Book — an example Callosum plugin UI.

A Callosum plugin is an app with a UI whose read-only data layer is the mind wiki's derived
pages. This one serves a browsable recipe book over `wiki/recipes/` — filter by ingredients
you have, open a recipe, cook. It never writes, and never touches `library/` originals or
`raw/` queues; new recipes appear here the moment `/callosum:catalog` lands them.

    python3 examples/recipe-book-ui/serve.py [mind-root] [--port 8765]

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


def load_recipes(mind_root):
    """The whole data layer: parse wiki/recipes/*.md into plain dicts."""
    recipes = []
    folder = os.path.join(mind_root, "wiki", "recipes")
    if not os.path.isdir(folder):
        return recipes
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".md") or name == "AGENTS.md":
            continue
        with open(os.path.join(folder, name), "r", encoding="utf-8") as f:
            content = f.read()
        fm, _ = mu.parse_frontmatter(content)
        fm = fm or {}
        _, body = mu.split_frontmatter(content)
        sections = mu.find_sections(body)
        ing_text = mu.section_text(body, sections, "ingredients") or ""
        ingredients = [re.sub(r"^[-*]\s*", "", l).strip()
                       for l in ing_text.splitlines() if l.strip().startswith(("-", "*"))]
        recipes.append({
            "slug": mu.slug_of(name),
            "title": fm.get("title", mu.slug_of(name)),
            "tags": fm.get("tags") or [],
            "domain": fm.get("domain", ""),
            "ingredients": ingredients,
            "body": body,
            "path": f"wiki/recipes/{name}",
        })
    return recipes


PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Recipe Book</title>
<style>
:root { color-scheme: light dark; font-family: -apple-system, system-ui, sans-serif; }
body { margin: 0 auto; max-width: 760px; padding: 1.5rem; line-height: 1.5; }
h1 { font-size: 1.4rem; } small { opacity: .6; }
input { width: 100%; padding: .6rem .8rem; font-size: 1rem; border-radius: 8px;
        border: 1px solid color-mix(in srgb, currentColor 25%, transparent);
        background: transparent; color: inherit; margin: .8rem 0 1.2rem; }
.card { border: 1px solid color-mix(in srgb, currentColor 15%, transparent);
        border-radius: 10px; padding: .9rem 1.1rem; margin-bottom: .8rem; cursor: pointer; }
.card:hover { border-color: color-mix(in srgb, currentColor 40%, transparent); }
.card h2 { margin: 0 0 .2rem; font-size: 1.05rem; }
.match { font-weight: 600; } .miss { opacity: .55; }
.tag { display: inline-block; font-size: .75rem; padding: .05rem .5rem; border-radius: 99px;
       background: color-mix(in srgb, currentColor 12%, transparent); margin-right: .3rem; }
#detail { white-space: pre-wrap; }
a { color: inherit; }
</style></head><body>
<h1>Recipe Book <small>— a Callosum plugin (data: wiki/recipes/)</small></h1>
<div id="list-view">
  <input id="q" placeholder="ingredients you have, comma separated (e.g. eggs, tomatoes)" autofocus>
  <div id="cards"></div>
</div>
<div id="detail-view" style="display:none">
  <p><a href="#" onclick="back();return false">&larr; all recipes</a></p>
  <div id="detail"></div>
</div>
<script>
let RECIPES = [];
const q = document.getElementById('q'), cards = document.getElementById('cards');
function terms() { return q.value.toLowerCase().split(',').map(s => s.trim()).filter(Boolean); }
function score(r, ts) {
  const ing = r.ingredients.join(' ').toLowerCase();
  const have = ts.filter(t => ing.includes(t));
  return { have, missing: ts.filter(t => !ing.includes(t)) };
}
function render() {
  const ts = terms();
  const rows = RECIPES.map(r => ({ r, s: score(r, ts) }))
    .sort((a, b) => b.s.have.length - a.s.have.length);
  cards.innerHTML = rows.map(({ r, s }) => `
    <div class="card" onclick="show('${r.slug}')">
      <h2>${r.title}</h2>
      ${ts.length ? `<div><span class="match">uses: ${s.have.join(', ') || '—'}</span>
        <span class="miss">${s.missing.length ? ' · not matched: ' + s.missing.join(', ') : ''}</span></div>` : ''}
      <div>${(r.tags || []).map(t => `<span class="tag">${t}</span>`).join('')}
        <small>${r.path}</small></div>
    </div>`).join('') || '<p>No recipe pages yet — run /callosum:catalog on files in raw/references/.</p>';
}
function show(slug) {
  const r = RECIPES.find(x => x.slug === slug);
  document.getElementById('detail').textContent = r.body;
  document.getElementById('list-view').style.display = 'none';
  document.getElementById('detail-view').style.display = 'block';
}
function back() {
  document.getElementById('detail-view').style.display = 'none';
  document.getElementById('list-view').style.display = 'block';
}
q.addEventListener('input', render);
fetch('/api/recipes').then(r => r.json()).then(d => { RECIPES = d; render(); });
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", nargs="?", default=None)
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    mind_root = os.path.abspath(args.root) if args.root else mu.resolve_default_mind_root()
    if not mind_root or not os.path.exists(os.path.join(mind_root, ".callosum")):
        print("no mind root found — pass one explicitly", file=sys.stderr)
        return 1

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/api/recipes"):
                payload = json.dumps(load_recipes(mind_root)).encode()
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

    print(f"Recipe Book on http://localhost:{args.port}  (data: {mind_root}/wiki/recipes/)")
    http.server.HTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    sys.exit(main())
