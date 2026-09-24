#!/usr/bin/env python3
"""Kinetic Idea Board — an example Callosum *actionable console* plugin.

The read-only board shows verdicts. This one adds an **Inbox** column of raw ideas
(`raw/ideas/`) and two action lanes: drag an inbox card into **Incubate** or **Research** and
the board runs the matching skill on it. The card then lands in the verdict column the skill
decided (Ripened / Conditional / Rejected), or gains a research page.

The board never writes the wiki. A drop POSTs {slug, action}; the server maps action → a fixed
skill command and runs it via `claude -p` with the mind root in env. The skill writes through
the prewrite gate and lands a commit — so every substrate guarantee holds. Actions are a closed
set; the slug is validated ([a-z0-9-]) and passed as an argv element, never shell-interpolated.

    python3 examples/idea-board-kinetic/serve.py [mind-root] [--port 8767]
    # set CALLOSUM_KINETIC_DRYRUN=1 to echo the command instead of running claude (for demo)

Stdlib only.
"""
import argparse
import http.server
import importlib.util
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
from scripts import mind_utils as mu  # noqa: E402

# closed action set — the ONLY things a card drop may trigger
ACTIONS = {
    "incubate": {"skill": "incubate", "label": "Incubate (research + verdict)"},
    "research": {"skill": "investigate", "label": "Research (deep-dive → research page)"},
}
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}$")

# reuse the read-only board's loader for the verdict columns
_spec = importlib.util.spec_from_file_location(
    "idea_ro", os.path.join(REPO, "examples", "idea-board-ui", "serve.py"))
_ro = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ro)


def inbox_ideas(mind_root):
    """Raw, un-incubated ideas — the Inbox column."""
    out = []
    d = os.path.join(mind_root, "raw", "ideas")
    if not os.path.isdir(d):
        return out
    for name in sorted(os.listdir(d)):
        if not name.endswith(".md"):
            continue
        with open(os.path.join(d, name), "r", encoding="utf-8") as f:
            body = f.read()
        first = next((l.strip("# ").strip() for l in body.splitlines() if l.strip()), name)
        out.append({"slug": mu.slug_of(name), "title": first[:80], "path": f"raw/ideas/{name}"})
    return out


def run_action(mind_root, slug, action):
    """Validate and invoke the skill. Returns (ok, message). Never writes the wiki itself."""
    if action not in ACTIONS:
        return False, f"unknown action {action!r}"
    if not SLUG_RE.match(slug or ""):
        return False, "invalid idea id"
    raw = os.path.join(mind_root, "raw", "ideas", f"{slug}.md")
    if not os.path.exists(raw):
        return False, f"no raw idea named {slug}"
    skill = ACTIONS[action]["skill"]
    prompt = f"/{skill} {slug}"
    env = {**os.environ, "CALLOSUM_MIND_ROOT": mind_root, "CALLOSUM_PLUGIN_ROOT": REPO}
    if os.environ.get("CALLOSUM_KINETIC_DRYRUN") == "1":
        return True, f"[dry-run] would run: claude -p {prompt!r} (skill={skill}, slug={slug})"
    try:
        r = subprocess.run(
            ["claude", "-p", prompt, "--dangerously-skip-permissions"],
            cwd=mind_root, env=env, capture_output=True, text=True, timeout=600)
    except FileNotFoundError:
        return False, "claude CLI not found on PATH"
    except subprocess.TimeoutExpired:
        return False, f"{skill} timed out"
    if r.returncode != 0:
        return False, f"{skill} failed: {(r.stderr or '').strip()[-300:]}"
    return True, f"{skill} done: {(r.stdout or '').strip()[-300:]}"


PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Idea Board (kinetic)</title>
<style>
:root { color-scheme: light dark; font-family: -apple-system, system-ui, sans-serif; }
body { margin: 0 auto; max-width: 1200px; padding: 1.5rem; line-height: 1.45; }
h1 { font-size: 1.4rem; } small { opacity: .6; }
#board { display: grid; grid-template-columns: repeat(6, 1fr); gap: .8rem; align-items: start; }
.col { border: 1px dashed transparent; border-radius: 10px; padding: .3rem; min-height: 80px; }
.col.action { border-color: color-mix(in srgb, currentColor 30%, transparent);
              background: color-mix(in srgb, currentColor 5%, transparent); }
.col.over { border-color: #2563eb; background: #2563eb18; }
.col h2 { font-size: .8rem; text-transform: uppercase; letter-spacing: .05em; opacity: .7; padding: 0 .3rem; }
.card { border: 1px solid color-mix(in srgb, currentColor 18%, transparent);
        border-radius: 8px; padding: .55rem .7rem; margin: .4rem .2rem; background: Canvas; }
.card[draggable=true] { cursor: grab; }
.card h3 { margin: 0; font-size: .9rem; }
.badge { font-size: .65rem; font-weight: 700; padding: .05rem .4rem; border-radius: 99px;
         background: #c2410c22; color: #c2410c; }
#toast { position: fixed; bottom: 1rem; left: 50%; transform: translateX(-50%);
         background: Canvas; border: 1px solid; border-radius: 8px; padding: .6rem 1rem;
         max-width: 90%; display: none; }
@media (max-width: 900px) { #board { grid-template-columns: 1fr 1fr; } }
</style></head><body>
<h1>Idea Board <small>— kinetic: drag an inbox idea into Incubate or Research</small></h1>
<div id="board"></div>
<div id="toast"></div>
<script>
let DATA = {};
const COLS = [
  {key: 'inbox', title: 'Inbox (raw)', drag: true},
  {key: 'incubate', title: '▶ Incubate', action: true},
  {key: 'research', title: '▶ Research', action: true},
  {key: 'RIPENED', title: 'Ripened'},
  {key: 'CONDITIONAL', title: 'Conditional'},
  {key: 'REJECTED', title: 'Rejected'},
];
function toast(msg) { const t = document.getElementById('toast'); t.textContent = msg; t.style.display = 'block';
  setTimeout(() => t.style.display = 'none', 6000); }
function cardHtml(i, drag) {
  return `<div class="card" ${drag ? 'draggable="true"' : ''} data-slug="${i.slug}"
    ondragstart="event.dataTransfer.setData('text/plain','${i.slug}')">
    <h3>${i.title} ${i.stale ? '<span class="badge">STALE</span>' : ''}</h3>
    <small>${i.path || ''}</small></div>`;
}
function render() {
  document.getElementById('board').innerHTML = COLS.map(c => {
    let items = [];
    if (c.key === 'inbox') items = DATA.inbox || [];
    else if (!c.action) items = (DATA.ideas || []).filter(i => i.verdict === c.key);
    const body = c.action
      ? `<div class="col action" data-action="${c.key}"
           ondragover="event.preventDefault();this.classList.add('over')"
           ondragleave="this.classList.remove('over')"
           ondrop="drop(event,'${c.key}')"><h2>${c.title}</h2><small style="padding:.3rem;opacity:.5">drop here</small></div>`
      : `<div class="col"><h2>${c.title}</h2>${items.map(i => cardHtml(i, c.drag)).join('')}</div>`;
    return body;
  }).join('');
}
function drop(ev, action) {
  ev.preventDefault();
  const slug = ev.dataTransfer.getData('text/plain');
  document.querySelectorAll('.col').forEach(c => c.classList.remove('over'));
  toast(`Running /${action === 'incubate' ? 'incubate' : 'investigate'} on ${slug}…`);
  fetch('/action', {method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({slug, action})})
    .then(r => r.json()).then(d => { toast(d.message); load(); });
}
function load() { fetch('/api/board').then(r => r.json()).then(d => { DATA = d; render(); }); }
load();
</script></body></html>"""


def board_data(mind_root):
    return {"inbox": inbox_ideas(mind_root), "ideas": _ro.load_ideas(mind_root),
            "actions": list(ACTIONS)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", nargs="?", default=None)
    ap.add_argument("--port", type=int, default=8767)
    args = ap.parse_args()
    mind_root = os.path.abspath(args.root) if args.root else mu.resolve_default_mind_root()
    if not mind_root or not os.path.exists(os.path.join(mind_root, ".callosum")):
        print("no mind root found — pass one explicitly", file=sys.stderr)
        return 1

    class Handler(http.server.BaseHTTPRequestHandler):
        def _send(self, code, payload, ctype="application/json"):
            body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path.startswith("/api/board"):
                self._send(200, board_data(mind_root))
            else:
                self._send(200, PAGE.encode(), "text/html; charset=utf-8")

        def do_POST(self):
            if self.path != "/action":
                self._send(404, {"ok": False, "message": "not found"})
                return
            length = int(self.headers.get("Content-Length", 0))
            try:
                req = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                self._send(400, {"ok": False, "message": "bad request"})
                return
            ok, msg = run_action(mind_root, req.get("slug", ""), req.get("action", ""))
            self._send(200, {"ok": ok, "message": msg})

        def log_message(self, *a):
            pass

    print(f"Kinetic Idea Board on http://localhost:{args.port}  (mind: {mind_root})")
    print(f"  actions: {', '.join(ACTIONS)}  |  dry-run: {os.environ.get('CALLOSUM_KINETIC_DRYRUN') == '1'}")
    http.server.HTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    sys.exit(main())
