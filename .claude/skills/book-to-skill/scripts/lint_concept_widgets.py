#!/usr/bin/env python3
"""
lint_concept_widgets.py — validate course-lesson concept widgets and the
theme-safety of bespoke static SVG.

Enforces the frozen contract in
`the-knowledge-guy/design-system/widgets.md`:

  WIDGET JSON (the `#kg-concept-widgets` island):
    * closed `type` enum: flow | toggle-state | stepper | slider | compare
    * required shared fields (id, type, surface∈{plate,illus}, title) and the
      per-type required fields (steps / toggles / slider+visual / panels)
    * coordinates within the fixed 0 0 640 280 viewBox (incl. ±w/2, ±h/2)
    * referential integrity: every edge from/to, every step active/activeEdges,
      every toggle nodeClass/edgeClass key references a declared node/edge id
    * theme-safety: any semantic value (ok/warn/crit/ins) requires
      surface:"illus"; edgeClass values ∈ {normal,emph}; plate kinds ∈
      {normal,accent,muted}; slider requires surface:"illus"
    * unique widget id per page

  BESPOKE STATIC SVG (the `#theory-illustration` slot):
    * NO hardcoded color: fill="#…"/stroke="#…"/rgb()/hsl()/style="…color…"
      (fill="none"/"currentColor", var(--…), stroke-opacity are allowed)
    * NO <script> or on*= handlers
    * (warn) every drawable shape carries a design-system class

Two entry modes:
  lint_concept_widgets.py --check-stdin     # gate ONE spec or SVG snippet on stdin
  lint_concept_widgets.py --page <file>     # audit one rendered course page
  lint_concept_widgets.py <dir>             # audit every *.html under a dir

Exit 1 on any hard ERROR; warnings exit 1 only with --strict.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

WIDGET_TYPES = {"flow", "toggle-state", "stepper", "slider", "compare"}
SURFACES = {"plate", "illus"}
SEMANTIC = {"ok", "warn", "crit", "ins"}
PLATE_KINDS = {"normal", "accent", "muted"}
ILLUS_KINDS = {"normal", "accent", "muted", "ok", "warn", "crit", "ins"}
EDGE_STATES = {"normal", "emph"}
VBW, VBH = 640, 280

# bespoke-SVG color hygiene
RE_HARD_COLOR = re.compile(r'(?:fill|stroke)\s*=\s*"(?![^"]*(?:none|currentColor|url\(|var\())[^"]*(?:#|rgb|hsl)', re.I)
RE_STYLE_COLOR = re.compile(r'style\s*=\s*"[^"]*(?:fill|stroke|color)\s*:', re.I)
RE_SCRIPT = re.compile(r'<script\b|\son[a-z]+\s*=', re.I)
RE_SHAPE = re.compile(r'<(rect|circle|ellipse|path|line|polygon|polyline|text)\b([^>]*)>', re.I)
RE_SVG_BLOCK = re.compile(r'<svg\b[\s\S]*?</svg>', re.I)
RE_ISLAND = re.compile(
    r'<script[^>]*id="kg-concept-widgets"[^>]*>([\s\S]*?)</script>', re.I)


def _xy_in_frame(x, y, w, h, label, errs):
    try:
        x, y, w, h = float(x), float(y), float(w), float(h)
    except (TypeError, ValueError):
        errs.append(f"{label}: x/y/w/h must be numbers")
        return
    if not (0 <= x - w / 2 and x + w / 2 <= VBW and 0 <= y - h / 2 and y + h / 2 <= VBH):
        errs.append(f"{label}: extends outside the {VBW}×{VBH} frame "
                    f"(center {x},{y} size {w}×{h})")


def validate_widget(w: dict) -> list[str]:
    e: list[str] = []
    wid = w.get("id", "<no-id>")
    typ = w.get("type")
    surface = w.get("surface")

    for f in ("id", "type", "surface", "title"):
        if not w.get(f):
            e.append(f"[{wid}] missing `{f}`")
    if typ not in WIDGET_TYPES:
        e.append(f"[{wid}] unknown type `{typ}`")
        return e
    if surface not in SURFACES:
        e.append(f"[{wid}] surface must be plate|illus")
        return e

    node_kinds = PLATE_KINDS if surface == "plate" else ILLUS_KINDS
    nodes = {n.get("id"): n for n in (w.get("nodes") or []) if n.get("id")}
    edges = {ed.get("id"): ed for ed in (w.get("edges") or []) if ed.get("id")}

    # node coords + kinds
    for nid, n in nodes.items():
        _xy_in_frame(n.get("x"), n.get("y"), n.get("w", 120), n.get("h", 52), f"[{wid}] node {nid}", e)
        k = n.get("kind", "normal")
        if k not in node_kinds:
            e.append(f"[{wid}] node {nid}: kind `{k}` not allowed on surface {surface}")
        if k in SEMANTIC and surface != "illus":
            e.append(f"[{wid}] node {nid}: semantic kind `{k}` requires surface:illus")

    # edge integrity
    for eid, ed in edges.items():
        for end in ("from", "to"):
            if ed.get(end) not in nodes:
                e.append(f"[{wid}] edge {eid}: `{end}` references unknown node `{ed.get(end)}`")

    # per-type
    if typ in ("flow", "stepper"):
        steps = w.get("steps") or []
        if not steps:
            e.append(f"[{wid}] {typ} needs a non-empty steps[]")
        for i, st in enumerate(steps):
            for nid in st.get("active", []):
                if nid not in nodes:
                    e.append(f"[{wid}] step {i}: active references unknown node `{nid}`")
            for eid in st.get("activeEdges", []):
                if eid not in edges:
                    e.append(f"[{wid}] step {i}: activeEdges references unknown edge `{eid}`")
    elif typ == "toggle-state":
        toggles = w.get("toggles") or []
        if not (1 <= len(toggles) <= 3):
            e.append(f"[{wid}] toggle-state needs 1-3 toggles")
        for t in toggles:
            for branch in ("on", "off"):
                br = t.get(branch) or {}
                for nid, kind in (br.get("nodeClass") or {}).items():
                    if nid not in nodes:
                        e.append(f"[{wid}] toggle {t.get('id')}: nodeClass references unknown node `{nid}`")
                    if kind not in node_kinds:
                        e.append(f"[{wid}] toggle {t.get('id')}: nodeClass `{kind}` not allowed on {surface}")
                    if kind in SEMANTIC and surface != "illus":
                        e.append(f"[{wid}] toggle {t.get('id')}: semantic `{kind}` requires surface:illus")
                for eid, state in (br.get("edgeClass") or {}).items():
                    if eid not in edges:
                        e.append(f"[{wid}] toggle {t.get('id')}: edgeClass references unknown edge `{eid}`")
                    if state not in EDGE_STATES:
                        e.append(f"[{wid}] toggle {t.get('id')}: edgeClass `{state}` must be normal|emph")
    elif typ == "slider":
        if surface != "illus":
            e.append(f"[{wid}] slider requires surface:illus (uses the crit state)")
        s = w.get("slider") or {}
        for f in ("min", "max", "step", "default", "threshold"):
            if s.get(f) is None:
                e.append(f"[{wid}] slider.{f} is required")
        vis = w.get("visual") or {}
        if vis.get("kind") != "bar":
            e.append(f"[{wid}] slider visual.kind must be 'bar'")
        for ref in ("fillNode", "capacityNode"):
            if vis.get(ref) not in nodes:
                e.append(f"[{wid}] slider visual.{ref} references unknown node `{vis.get(ref)}`")
        for f in ("below", "atOrAbove"):
            if not (w.get(f) or {}).get("caption"):
                e.append(f"[{wid}] slider.{f}.caption is required")
    elif typ == "compare":
        panels = w.get("panels") or []
        if len(panels) not in (2, 4):
            e.append(f"[{wid}] compare needs exactly 2 or 4 panels")
        pids = set()
        for p in panels:
            pid = p.get("id")
            if not pid or pid in pids:
                e.append(f"[{wid}] compare panel id `{pid}` missing or duplicate")
            pids.add(pid)
            if not p.get("detail"):
                e.append(f"[{wid}] compare panel {pid}: detail is required")
            _xy_in_frame(p.get("x"), p.get("y"), p.get("w", 260), p.get("h", 120), f"[{wid}] panel {pid}", e)
    return e


def validate_island(text: str) -> list[str]:
    e: list[str] = []
    try:
        specs = json.loads(text)
    except json.JSONDecodeError as ex:
        return [f"#kg-concept-widgets island is not valid JSON: {ex}"]
    if not isinstance(specs, list):
        return ["#kg-concept-widgets island must be a JSON array"]
    seen = set()
    for w in specs:
        if not isinstance(w, dict):
            e.append("island entry is not an object")
            continue
        wid = w.get("id")
        if wid in seen:
            e.append(f"[{wid}] duplicate widget id on the page")
        seen.add(wid)
        e += validate_widget(w)
    return e


def svg_hygiene(markup: str, label: str) -> tuple[list[str], list[str]]:
    errs, warns = [], []
    for block in RE_SVG_BLOCK.findall(markup):
        if RE_HARD_COLOR.search(block):
            errs.append(f"{label}: hardcoded fill/stroke color (use a design-system class or var(--…))")
        if RE_STYLE_COLOR.search(block):
            errs.append(f"{label}: inline style sets fill/stroke/color")
        if RE_SCRIPT.search(block):
            errs.append(f"{label}: static SVG must not contain <script> or on*= handlers")
        for tag, attrs in RE_SHAPE.findall(block):
            if "class=" not in attrs:
                warns.append(f"{label}: <{tag}> without a design-system class")
    return errs, warns


def audit_page(path: Path) -> tuple[list[str], list[str]]:
    html = path.read_text(encoding="utf-8", errors="replace")
    errs, warns = [], []
    m = RE_ISLAND.search(html)
    if m:
        errs += [f"{path.name}: {x}" for x in validate_island(m.group(1))]
    # bespoke static SVG color hygiene (engine-built SVG is runtime, not in source)
    body = html.split("<body", 1)[-1]
    se, sw = svg_hygiene(body, path.name)
    errs += se
    warns += sw
    return errs, warns


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", help="a dir of rendered course pages to audit")
    ap.add_argument("--page", help="audit a single rendered course-page HTML file")
    ap.add_argument("--check-stdin", action="store_true",
                    help="validate ONE widget spec (JSON) or SVG snippet from stdin")
    ap.add_argument("--strict", action="store_true", help="exit non-zero on warnings too")
    args = ap.parse_args()

    errs: list[str] = []
    warns: list[str] = []

    if args.check_stdin:
        data = sys.stdin.read().strip()
        if data[:1] in "[{":
            specs = data if data[:1] == "[" else "[" + data + "]"
            errs += validate_island(specs)
        else:
            se, sw = svg_hygiene(data, "stdin")
            errs += se
            warns += sw
    elif args.page:
        e, w = audit_page(Path(args.page))
        errs += e
        warns += w
    elif args.path:
        files = sorted(Path(args.path).rglob("*.html"))
        if not files:
            print(f"No *.html under {args.path} — nothing to audit.")
            return 0
        for f in files:
            e, w = audit_page(f)
            errs += e
            warns += w
    else:
        ap.error("give a dir, --page <file>, or --check-stdin")

    for x in errs:
        print(f"  ERROR  {x}")
    for x in warns:
        print(f"  warn   {x}")
    print(f"\n{len(errs)} error(s), {len(warns)} warning(s).")
    if errs:
        return 1
    return 1 if (args.strict and warns) else 0


if __name__ == "__main__":
    raise SystemExit(main())
