#!/usr/bin/env python3
"""Idea Kanban — a Callosum *actionable console* over the full ripening pipeline.

The read-only board (`idea-board-ui`) shows verdicts; the kinetic sketch
(`idea-board-kinetic`) triggers skills synchronously. This addon manages the whole
flow as a pipeline: **Queued** (raw/ideas/) → **Ripening** (live /callosum:incubate or
/callosum:investigate runs) → the verdict columns (/callosum:incubate's terminal states, plus any
verdict value the data itself coins).

What "manage" means here:

- Drag an inbox card into an action lane and the run starts **asynchronously** — the
  card moves to Ripening immediately, several ideas can ripen in parallel, and the
  board polls until each run resolves. When the skill lands its verdict page (and
  archives the raw idea), the card leaves Ripening and appears in the verdict column
  the skill chose. A run whose process dies without a landed verdict is marked FAILED
  with its log tail, instead of vanishing.
- A STALE verdict card (a Basis page moved after the verdict) carries a re-incubate
  button: the board hands the *page path* back to /callosum:incubate, the one sanctioned
  re-write of an existing idea page.

The substrate rules hold exactly as in the other plugins: the board never writes the
wiki. Runs are a closed action set mapped to fixed skill invocations (`claude -p
"/<skill> <arg>"`, argv-built, never shell-interpolated). The only state the addon
persists is its own run registry under `<mind>/.idea-kanban/` — outside `wiki/`,
`raw/`, `library/`, and `archive/`, so lint never sees it.

Generality: the verdict vocabulary is not baked in. The declared terminal order below
exists only to give the board a stable shape; any verdict value observed in the data
that is not in it gets its own column appended after. Nothing in core knows this
addon exists.

    python3 examples/idea-kanban/serve.py [mind-root] [--port 8768]
    # CALLOSUM_KANBAN_DRYRUN=1 records runs without spawning claude (demo)

Stdlib only.
"""
import argparse
import datetime
import http.server
import importlib.util
import json
import os
import re
import subprocess
import sys
import threading
import time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
from scripts import mind_utils as mu  # noqa: E402

# Reuse the read-only board's primitives (Basis-staleness regex, page registry).
_spec = importlib.util.spec_from_file_location(
    "idea_ro", os.path.join(REPO, "examples", "idea-board-ui", "serve.py"))
_ro = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ro)

# /callosum:incubate's declared verdict vocabulary — column ORDER only. Any verdict observed
# in the data outside this set still gets a column (appended, sorted).
TERMINAL_ORDER = ["RIPENED", "CONDITIONAL", "REJECTED"]

# Closed action set — the ONLY things the board may trigger. `source` says which
# column a card must come from; `arg` says what the skill receives.
ACTIONS = {
    "incubate": {"skill": "incubate", "source": "inbox", "arg": "slug",
                 "label": "Incubate (research + verdict)"},
    "research": {"skill": "investigate", "source": "inbox", "arg": "slug",
                 "label": "Research (deep-dive → research page)"},
    "reincubate": {"skill": "incubate", "source": "verdicts", "arg": "path",
                   "label": "Re-incubate (stale verdict → fresh verdict)"},
}
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}$")
PAGE_PATH_RE = re.compile(r"^wiki/ideas/[a-z0-9][a-z0-9/._-]{0,200}\.md$")

STATE_DIR = ".idea-kanban"          # under the mind root; never under wiki/
KEEP_FINISHED = 50                  # finished runs retained in the registry
REGISTRY_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Data layer (read-only over the mind)
# ---------------------------------------------------------------------------

def inbox_ideas(mind_root):
    """Queued column: raw, un-incubated ideas."""
    out = []
    d = os.path.join(mind_root, "raw", "ideas")
    if not os.path.isdir(d):
        return out
    for name in sorted(os.listdir(d)):
        if not name.endswith(".md"):
            continue
        with open(os.path.join(d, name), "r", encoding="utf-8") as f:
            body = f.read()
        fm, _ = mu.parse_frontmatter(body)
        _, page_body = mu.split_frontmatter(body)
        heading = next((l.strip("# ").strip() for l in (page_body or body).splitlines()
                        if l.strip().startswith("#")), "")
        first_text = next((l.strip() for l in (page_body or body).splitlines()
                           if l.strip() and not l.strip().startswith("#")), "")
        title = str((fm or {}).get("title") or heading or first_text or mu.slug_of(name))
        out.append({"slug": mu.slug_of(name), "title": title[:80],
                    "path": f"raw/ideas/{name}"})
    return out


def verdict_ideas(mind_root):
    """Verdict cards, reusing the read-only board's staleness detection but keeping
    each page's true verdict string (the sketch coerces unknowns to RIPENED; the
    kanban surfaces emergent verdicts as their own columns)."""
    ideas = _ro.load_ideas(mind_root)
    for card in ideas:
        full = os.path.join(mind_root, card["path"])
        try:
            with open(full, "r", encoding="utf-8") as f:
                fm, _ = mu.parse_frontmatter(f.read())
        except OSError:
            continue
        raw = str((fm or {}).get("verdict", "")).strip().upper()
        if raw:
            card["verdict"] = raw
    return ideas


def verdict_columns(ideas):
    """Declared terminal order first, then any verdict the data coined, sorted."""
    observed = {str(i.get("verdict", "")).upper() for i in ideas}
    emergent = sorted(v for v in observed if v and v not in TERMINAL_ORDER)
    return TERMINAL_ORDER + emergent


# ---------------------------------------------------------------------------
# Run registry — the addon's own state, outside every governed folder
# ---------------------------------------------------------------------------

def registry_path(mind_root):
    return os.path.join(mind_root, STATE_DIR, "runs.json")


def load_registry(mind_root):
    try:
        with open(registry_path(mind_root), "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("runs"), list):
            return data["runs"]
    except (OSError, json.JSONDecodeError):
        pass
    return []


def save_registry(mind_root, runs):
    d = os.path.dirname(registry_path(mind_root))
    os.makedirs(d, exist_ok=True)
    tmp = registry_path(mind_root) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"runs": runs}, f, indent=2)
    os.replace(tmp, registry_path(mind_root))


def _pid_alive(pid):
    try:
        os.kill(int(pid), 0)
    except (OSError, TypeError, ValueError):
        return False
    return True


def _resolved(mind_root, run, verdict_slugs):
    """Did the skill land its output for this run?"""
    if run.get("source") == "verdicts":
        page = os.path.join(mind_root, run.get("page_path", ""))
        try:
            return os.path.getmtime(page) >= float(run.get("started_epoch", 0))
        except (OSError, TypeError, ValueError):
            return False
    # inbox run: a verdict page with the slug appeared, or the raw file was archived
    if run["slug"] in verdict_slugs:
        return True
    return not os.path.exists(os.path.join(mind_root, "raw", "ideas", run["slug"] + ".md"))


def _log_tail(mind_root, run, limit=400):
    try:
        with open(os.path.join(mind_root, run.get("log", "")), "r",
                  encoding="utf-8", errors="replace") as f:
            return f.read()[-limit:]
    except OSError:
        return ""


def reconcile(mind_root, verdict_slugs, pid_alive=_pid_alive):
    """Fold process liveness + filesystem truth into run statuses. Registry writes
    are the ONLY writes this addon ever makes, and they stay under .idea-kanban/."""
    changed = False
    with REGISTRY_LOCK:
        runs = load_registry(mind_root)
        for run in runs:
            if run.get("status") != "running":
                continue
            if pid_alive(run.get("pid")):
                continue
            if _resolved(mind_root, run, verdict_slugs):
                run["status"] = "done"
                run["detail"] = "verdict landed"
            else:
                run["status"] = "failed"
                run["detail"] = ("process exited without a landed verdict. "
                                 + _log_tail(mind_root, run)).strip()
            run["ended"] = datetime.datetime.now().isoformat(timespec="seconds")
            changed = True
        finished = [r for r in runs if r.get("status") != "running"]
        if len(finished) > KEEP_FINISHED:
            excess = len(finished) - KEEP_FINISHED
            pruned = []
            for r in runs:
                if r.get("status") != "running" and excess > 0:
                    excess -= 1
                    continue
                pruned.append(r)
            runs = pruned
            changed = True
        if changed:
            save_registry(mind_root, runs)
    return runs


# ---------------------------------------------------------------------------
# Actions — closed set, argv-built, never shell-interpolated
# ---------------------------------------------------------------------------

def spawn_run(mind_root, slug, action, dry_run=None, popen=subprocess.Popen,
              pid_alive=_pid_alive):
    """Validate and start a run. Returns (ok, message). Never writes the wiki."""
    spec = ACTIONS.get(action)
    if spec is None:
        return False, f"unknown action {action!r}"
    if not SLUG_RE.match(slug or ""):
        return False, "invalid idea id"
    ideas = verdict_ideas(mind_root)
    active = [r for r in reconcile(mind_root, {i["slug"] for i in ideas},
                                   pid_alive=pid_alive)
              if r.get("status") == "running" and r.get("slug") == slug]
    if active:
        return False, f"{slug} is already {active[0]['action']}ing"

    if spec["source"] == "inbox":
        if not os.path.exists(os.path.join(mind_root, "raw", "ideas", f"{slug}.md")):
            return False, f"no raw idea named {slug}"
        arg, page_path = slug, None
    else:
        card = next((i for i in ideas if i["slug"] == slug), None)
        if card is None:
            return False, f"no published idea named {slug}"
        page_path = card["path"]
        if not PAGE_PATH_RE.match(page_path) or \
                not os.path.exists(os.path.join(mind_root, page_path)):
            return False, f"invalid idea page path {page_path!r}"
        arg = page_path

    skill = spec["skill"]
    prompt = f"/{skill} {arg}"
    env = {**os.environ, "CALLOSUM_MIND_ROOT": mind_root, "CALLOSUM_PLUGIN_ROOT": REPO}
    if dry_run is None:
        dry_run = os.environ.get("CALLOSUM_KANBAN_DRYRUN") == "1"

    now = datetime.datetime.now().isoformat(timespec="seconds")
    run = {"slug": slug, "action": action, "skill": skill, "arg": arg,
           "source": spec["source"], "page_path": page_path,
           "started": now, "started_epoch": time.time(), "status": "running"}
    if dry_run:
        run.update(status="dry-run", ended=now,
                   detail=f"[dry-run] would run: claude -p {prompt!r}")
        with REGISTRY_LOCK:
            runs = load_registry(mind_root)
            runs.append(run)
            save_registry(mind_root, runs)
        return True, run["detail"]

    log_rel = os.path.join(STATE_DIR, "logs",
                           f"{int(run['started_epoch'])}-{slug}-{action}.log")
    log_abs = os.path.join(mind_root, log_rel)
    os.makedirs(os.path.dirname(log_abs), exist_ok=True)
    try:
        with open(log_abs, "w", encoding="utf-8") as logf:
            proc = popen(["claude", "-p", prompt, "--dangerously-skip-permissions"],
                         cwd=mind_root, env=env, stdout=logf, stderr=subprocess.STDOUT)
    except OSError as exc:
        detail = "claude CLI not found on PATH" if isinstance(exc, FileNotFoundError) else \
            f"cannot start run: {exc}"
        run.update(status="failed", ended=now, detail=detail,
                   log=log_rel.replace(os.sep, "/"))
        with REGISTRY_LOCK:
            runs = load_registry(mind_root)
            runs.append(run)
            save_registry(mind_root, runs)
        return False, detail
    run["pid"] = proc.pid
    run["log"] = log_rel.replace(os.sep, "/")
    with REGISTRY_LOCK:
        runs = load_registry(mind_root)
        runs.append(run)
        save_registry(mind_root, runs)
    return True, f"/{skill} started on {slug} (pid {proc.pid}) — watch the Ripening column"


def board_data(mind_root):
    ideas = verdict_ideas(mind_root)
    runs = reconcile(mind_root, {i["slug"] for i in ideas})
    return {
        "inbox": inbox_ideas(mind_root),
        "ripening": [r for r in runs if r.get("status") == "running"],
        "ideas": ideas,
        "columns": verdict_columns(ideas),
        "actions": {k: {"label": v["label"], "source": v["source"]}
                    for k, v in ACTIONS.items()},
        "runs": [r for r in runs if r.get("status") != "running"][-10:],
    }


PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Idea Kanban</title>
<style>
:root { color-scheme: light dark; font-family: -apple-system, system-ui, sans-serif; }
body { margin: 0 auto; max-width: 1400px; padding: 1.5rem; line-height: 1.45; }
h1 { font-size: 1.4rem; } small { opacity: .6; }
#board { display: grid; grid-auto-flow: column; grid-auto-columns: minmax(180px, 1fr);
         gap: .8rem; align-items: start; overflow-x: auto; }
.col { border: 1px dashed transparent; border-radius: 10px; padding: .3rem; min-height: 80px; }
.col.action { border-color: color-mix(in srgb, currentColor 30%, transparent);
              background: color-mix(in srgb, currentColor 5%, transparent); }
.col.over { border-color: #2563eb; background: #2563eb18; }
.col h2 { font-size: .8rem; text-transform: uppercase; letter-spacing: .05em;
          opacity: .7; padding: 0 .3rem; }
.card { border: 1px solid color-mix(in srgb, currentColor 18%, transparent);
        border-radius: 8px; padding: .55rem .7rem; margin: .4rem .2rem; background: Canvas; }
.card[draggable=true] { cursor: grab; }
.card h3 { margin: 0; font-size: .9rem; }
.badge { font-size: .65rem; font-weight: 700; padding: .05rem .4rem; border-radius: 99px;
         background: #c2410c22; color: #c2410c; }
.badge.run { background: #2563eb22; color: #2563eb; }
.badge.fail { background: #dc262622; color: #dc2626; }
.badge.ok { background: #16a34a22; color: #16a34a; }
button.mini { font-size: .65rem; border: 1px solid; border-radius: 99px; background: none;
              color: inherit; padding: .05rem .5rem; cursor: pointer; opacity: .75; }
#toast { position: fixed; bottom: 1rem; left: 50%; transform: translateX(-50%);
         background: Canvas; border: 1px solid; border-radius: 8px; padding: .6rem 1rem;
         max-width: 90%; display: none; z-index: 2; }
#runs { margin-top: 1.5rem; font-size: .8rem; opacity: .85; }
#runs .r { padding: .15rem .3rem; border-bottom: 1px solid color-mix(in srgb, currentColor 10%, transparent); }
@media (max-width: 900px) { #board { grid-auto-flow: row; grid-auto-columns: unset; } }
</style></head><body>
<h1>Idea Kanban <small>— Queued &rarr; Ripening &rarr; verdict. Drag an idea into a lane.</small></h1>
<div id="board"></div>
<div id="runs"></div>
<div id="toast"></div>
<script>
let DATA = {};
function toast(msg) { const t = document.getElementById('toast'); t.textContent = msg;
  t.style.display = 'block'; setTimeout(() => t.style.display = 'none', 7000); }
function esc(s) { return String(s).replace(/[&<>"]/g, c =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function elapsed(r) { const s = Math.max(0, (Date.now() - new Date(r.started)) / 1000);
  return s < 60 ? Math.round(s) + 's' : Math.round(s / 60) + 'm'; }
function cardHtml(i, drag, staleBtn) {
  return `<div class="card" ${drag ? 'draggable="true"' : ''}
    ondragstart="event.dataTransfer.setData('text/plain','${esc(i.slug)}')">
    <h3>${esc(i.title)} ${i.stale ? '<span class="badge">STALE</span>' : ''}</h3>
    <small>${esc(i.path || '')}</small>
    ${staleBtn ? `<div><button class="mini" onclick="act('${esc(i.slug)}','reincubate')">&#8635; re-incubate</button></div>` : ''}
  </div>`;
}
function runHtml(r) {
  return `<div class="card"><h3>${esc(r.slug)} <span class="badge run">${esc(r.action)}&hellip; ${elapsed(r)}</span></h3>
    <small>started ${esc(r.started)}</small></div>`;
}
function render() {
  const cols = [
    {key: 'inbox', title: 'Queued', cards: (DATA.inbox || []).map(i => cardHtml(i, true))},
    {key: 'incubate', title: '&#9654; Incubate', action: true},
    {key: 'research', title: '&#9654; Research', action: true},
    {key: 'ripening', title: `Ripening (${(DATA.ripening || []).length})`,
     cards: (DATA.ripening || []).map(runHtml)},
  ].concat((DATA.columns || []).map(v => ({key: v, title: v,
    cards: (DATA.ideas || []).filter(i => i.verdict === v)
      .map(i => cardHtml(i, false, !!i.stale))})));
  document.getElementById('board').innerHTML = cols.map(c => c.action
    ? `<div class="col action" ondragover="event.preventDefault();this.classList.add('over')"
        ondragleave="this.classList.remove('over')" ondrop="drop(event,'${c.key}')">
        <h2>${c.title}</h2><small style="padding:.3rem;opacity:.5">drop here</small></div>`
    : `<div class="col"><h2>${c.title}</h2>${c.cards.join('')}</div>`).join('');
  const runs = DATA.runs || [];
  document.getElementById('runs').innerHTML = runs.length
    ? '<h2 style="font-size:.8rem;opacity:.7">RECENT RUNS</h2>' + runs.slice().reverse().map(r =>
      `<div class="r"><span class="badge ${r.status === 'failed' ? 'fail' : r.status === 'done' ? 'ok' : ''}">${esc(r.status)}</span>
       ${esc(r.action)} ${esc(r.slug)} — ${esc(r.started)}${r.detail ? ' — ' + esc(r.detail) : ''}</div>`).join('')
    : '';
}
function act(slug, action) {
  toast(`Running ${action} on ${slug}…`);
  fetch('/action', {method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({slug, action})})
    .then(r => r.json()).then(d => { toast(d.message); load(); });
}
function drop(ev, action) { ev.preventDefault();
  document.querySelectorAll('.col').forEach(c => c.classList.remove('over'));
  act(ev.dataTransfer.getData('text/plain'), action); }
function load() { fetch('/api/board').then(r => r.json()).then(d => {
  DATA = d; render();
  if ((d.ripening || []).length) setTimeout(load, 4000); }); }
load();
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", nargs="?", default=None)
    ap.add_argument("--port", type=int, default=8768)
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
            ok, msg = spawn_run(mind_root, req.get("slug", ""), req.get("action", ""))
            self._send(200, {"ok": ok, "message": msg})

        def log_message(self, *a):
            pass

    print(f"Idea Kanban on http://localhost:{args.port}  (mind: {mind_root})")
    print(f"  actions: {', '.join(ACTIONS)}  |  dry-run: {os.environ.get('CALLOSUM_KANBAN_DRYRUN') == '1'}")
    http.server.ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    sys.exit(main())
