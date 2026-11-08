"""A report drawn as a system diagram: the parts of the assessed system, its trust
boundary, and the part each risk sits on.

The picture is built from what the report already holds, so no report needs a hand-made
drawing, and it is drawn again whenever the report changes: nothing is stored beside the
report that could go stale.

- Outside the boundary: who or what starts each risk (`source.who`). The model's own
  failures (`model-*`) have no box of their own: the model is the system box.
- Inside: the system itself, the parts it takes content from (the channel a finding
  crosses on its way in) and the parts its output reaches (where a `model-output` path
  lands, named by the catalog weakness). A report with a surface ledger draws its rows
  instead, and a finding sits on the row whose outcome names it.
- A box's colour is its worst risk, and its sublabel says the same in words, because
  colour is never the only carrier of severity.

Archify does the drawing. It needs Node, so `keel up` still runs without it: the page
says once that the diagram is not available on this machine.
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from keel.schemas.report import Finding, Report

ORDER = {"high": 0, "medium": 1, "low": 2}

# Archify colours boxes by kind; the page maps each kind onto its own risk tokens.
KIND = {"high": "security", "medium": "messagebus", "low": "frontend", None: "backend"}
LEGEND = {
    "security": "High risk", "messagebus": "Medium risk", "frontend": "Low risk",
    "backend": "No risk found", "external": "Outside the system",
}
# Roles and kinds onto the tokens of web/src/styles.css. Severity colours are the only
# colours; the structure stays graphite.
TOKENS = (
    "text=--ink,muted=--ink-2,line=--rule,arrow=--ink-3,accent=--ink-2,surface=--card,region=--ink-3,"
    "security=--hi,messagebus=--md,frontend=--lo,backend=--ink-3,external=--ink-3,cloud=--ink-3,database=--ink-3"
)

# Plain words for who or what starts a risk (catalog/source.yaml). `error` is a defect in
# the code or its configuration, not the model's mistake: the model's own failures are
# the system box.
WHO = {
    "external-attacker": "External attacker", "supply-chain": "Supply chain",
    "internal": "Insider or user", "error": "Bug or bad setup", "accident": "A user's slip",
}
# The part a path comes in from, by its channel. `user-input`, `training-data` and no
# channel reach the model directly: those risks sit on the system box itself.
INWARD = {"retrieved-content": "knowledge-base", "memory": "memory", "agent-message": "agents", "tool-output": "tool"}
# The parts by name. Where a model-output path lands is the catalog's component for it.
PART = {
    "knowledge-base": "Retrieved documents", "memory": "Memory", "agents": "Other agents",
    "tool": "Tools it can call", "downstream": "Where output goes",
    "identity-store": "Accounts and keys", "config": "Configuration",
}
LEDGER_SIDE = {"entry": "in", "data": "in", "file": "in", "tool": "out"}
# A box label is drawn at one size; a longer one is cut here and given whole in its card.
LABEL_MAX = 20


@dataclass
class Box:
    id: str
    name: str
    side: str = "in"  # in: the system reads it, out: its output reaches it, outside: starts risks
    risks: list[Finding] = field(default_factory=list)
    note: str = ""

    @property
    def label(self) -> str:
        n = self.name.strip()
        return n if len(n) <= LABEL_MAX else n[: LABEL_MAX - 1].rstrip() + "…"

    @property
    def sub(self) -> str:
        """The box's risks in words, so colour is never the only sign of severity."""
        if self.side == "outside":
            return f"starts {plural(len(self.risks), 'risk')}"
        return f"{plural(len(self.risks), 'risk')} · {worst(self.risks)}" if self.risks else "no risk found"


def plural(n: int, one: str) -> str:
    return f"{n} {one}{'' if n == 1 else 's'}"


def worst(risks: list[Finding]) -> str | None:
    return min((f.risk.severity for f in risks), key=ORDER.__getitem__, default=None)


def _landing(f: Finding, threats: dict[str, Any]) -> str:
    """The catalog component a model-output path lands on, `downstream` when unnamed."""
    for w in (threats.get(f.id) or {}).get("weaknesses") or []:
        if f.attack_surface in (w.get("surface") or []) and w.get("component") in PART:
            return w["component"]
    return "downstream"


class Picture:
    """The boxes and arrows of one report, before any layout. A part the system both
    reads and writes is one box, on the reading side."""

    def __init__(self, report: Report, threats: dict[str, Any]):
        self.core = Box("system", report.system_name, side="core")
        self.boxes: dict[str, Box] = {}
        self.actors: dict[str, Box] = {}
        self.edges: dict[tuple[str, str], None] = {}  # an ordered set, one arrow per pair
        on_row: dict[str, Box] = {}
        found = {f.id for f in report.findings}
        for s in report.surfaces:
            box = self._box(f"s-{s.id.lower()}", s.name, LEDGER_SIDE[s.kind])
            box.note = s.note or ("" if set(s.outcome) & found or not s.outcome
                                  else "Every path here was ruled out or waits on an answer.")
            for fid in s.outcome:
                on_row.setdefault(fid, box)
            self._edge(*((box.id, "system") if box.side == "in" else ("system", box.id)))

        for f in report.findings:
            actor = self._actor(f.source.who)
            ch = f.attack_surface
            if f.id in on_row:
                box = on_row[f.id]
                into = box.id if box.side == "in" else "system"
            elif ch in INWARD:
                box = self._box(INWARD[ch], PART[INWARD[ch]], "in")
                box.side = "in"
                self._edge(box.id, "system")
                into = box.id
            elif ch == "model-output":
                part = _landing(f, threats)
                box = self._box(part, PART[part], "out")
                self._edge("system", box.id)
                into = "system"
            else:
                box, into = self.core, "system"
            box.risks.append(f)
            if actor:
                actor.risks.append(f)
                self._edge(actor.id, into)

    def _box(self, bid: str, name: str, side: str) -> Box:
        return self.boxes.setdefault(bid, Box(bid, name, side))

    def _actor(self, who: str) -> Box | None:
        if who not in WHO:
            return None
        return self.actors.setdefault(who, Box(f"who-{who}", WHO[who], side="outside"))

    def _edge(self, a: str, b: str) -> None:
        if (b, a) not in self.edges:
            self.edges[(a, b)] = None


# Two shapes of the same picture, each drawn so its labels stay at 12 px or more. The
# system's own parts stand in one column, the parts it reads above it and the parts its
# output reaches below, so an arrow between them is short or runs down the side lane.
# Wide: who starts the risks in a column to the left, for a report column of 620 px and
# up (a laptop: 689 to 975 px). Narrow: everything in one column, for a phone.
# web/src/styles.css switches at 620.
WIDE = {"cellW": 190, "cellH": 60, "gapX": 64, "gapY": 30}
# The phone column stands off the left edge: arrows that skip boxes stack their lanes there.
NARROW = {"cellW": 166, "cellH": 60, "gapX": 40, "gapY": 30, "origin": [72, 80]}
WIDTH = {"wide": 620, "narrow": 340}


def _beside(actors: list[Box], edges: dict, row_of: dict[str, int], rows: int) -> list[tuple[Box, int]]:
    """Each outside box level with the parts it points at, so its arrows stay short.
    The one with the most arrows goes first; a taken row passes to the nearest free one."""
    def targets(a: Box) -> list[int]:
        return [row_of[b] for (x, b) in edges if x == a.id and b in row_of]

    free, placed = list(range(max(rows, len(actors)))), []
    for a in sorted(actors, key=lambda a: -len(targets(a))):
        t = targets(a)
        want = sum(t) / len(t) if t else rows / 2
        row = min(free, key=lambda r: (abs(r - want), r))
        free.remove(row)
        placed.append((a, row))
    return placed


def candidate(report: Report, threats: dict[str, Any], shape: str = "wide") -> dict[str, Any]:
    """The Archify architecture candidate for this report."""
    p = Picture(report, threats)
    column = ([b for b in p.boxes.values() if b.side == "in"] + [p.core]
              + [b for b in p.boxes.values() if b.side == "out"])
    actors = list(p.actors.values())
    if shape == "wide":
        layout = {"mode": "grid", "cols": 2, **WIDE}
        cells = [(b, 1, r) for r, b in enumerate(column)]
        cells += [(b, 0, r) for b, r in _beside(actors, p.edges, {b.id: r for b, _, r in cells}, len(column))]
        lane = "right"
    else:
        layout = {"mode": "grid", "cols": 1, **NARROW}
        cells = [(b, 0, r) for r, b in enumerate(actors + column)]
        lane = "left"
    size = [layout["cellW"], layout["cellH"]]
    at = {b.id: (col, row) for b, col, row in cells}

    def arrow(a: str, b: str) -> dict[str, Any]:
        c: dict[str, Any] = {"id": f"c-{a}-{b}", "from": a, "to": b}
        (ca, ra), (cb, rb) = at[a], at[b]
        # Across the boxes between, or into the boundary past its label: take the lane.
        if ca == cb and (abs(ra - rb) > 1 or (lane == "left" and a.startswith("who-"))):
            c["fromSide"] = c["toSide"] = lane
        elif ca != cb:  # from the outside column: across the empty gap between the two
            c["fromSide"], c["toSide"] = "right", "left"
        return c

    components = [{
        "id": b.id, "label": b.label, "sublabel": b.sub, "col": col, "row": row, "size": size,
        "type": "external" if b.side == "outside" else KIND[worst(b.risks)],
    } for b, col, row in cells]
    kinds = {c["type"] for c in components}
    return {
        "schema_version": 1,
        "diagram_type": "architecture",
        "meta": {
            "title": f"{report.system_name}: where the risks sit",
            "output": "diagram.html",
            "legend": {"mode": "auto", "entries": {k: {"label": LEGEND[k]} for k in LEGEND if k in kinds}},
        },
        "layout": layout,
        "components": components,
        "boundaries": [{
            "kind": "region", "label": f"{report.system_name}: trust boundary",
            "wraps": [b.id for b in column],
        }],
        # No labels on arrows: in a column this narrow they land on the boxes.
        "connections": [arrow(a, b) for (a, b) in p.edges],
    }


def details(report: Report, threats: dict[str, Any]) -> dict[str, str]:
    """Each box's card: its whole name when the label was cut, then the risks on it
    (or that it starts), each a link to its page, worst first."""
    p = Picture(report, threats)
    base = html.escape(f"/reports/{report.system_id}/{report.date}")
    out = {}
    for b in [*p.actors.values(), p.core, *p.boxes.values()]:
        parts = [f"<b>{html.escape(b.name)}</b>"] if b.label != b.name.strip() else []
        if b.risks:
            items = "".join(
                f'<li><a href="{base}/{html.escape(f.id)}">{html.escape(_title(f, threats))}</a> · {f.risk.severity}</li>'
                for f in sorted(b.risks, key=lambda f: ORDER[f.risk.severity])
            )
            parts.append(f'<ul class="archify-risks">{items}</ul>')
        elif b.note:
            parts.append(html.escape(b.note))
        if parts:
            out[b.id] = "".join(parts)
    return out


def _title(f: Finding, threats: dict[str, Any]) -> str:
    t = (threats.get(f.id) or {}).get("title")
    if t:
        return t
    first = f.scenario.split(". ")[0].rstrip(".")
    return first[:110].rsplit(" ", 1)[0] + "..." if len(first) > 110 else first or f.id


# --------------------------------------------------------------------------- #
# Drawing
# --------------------------------------------------------------------------- #
class Unavailable(Exception):
    """The diagram cannot be drawn here. The message is said to the reader as is."""


def archify_dir() -> Path | None:
    """Where the Archify skill lives: KEEL_ARCHIFY, else the usual skill folders."""
    env = os.environ.get("KEEL_ARCHIFY")
    places = [Path(env)] if env else [
        Path.home() / ".agents" / "skills" / "archify", Path.home() / ".claude" / "skills" / "archify",
    ]
    return next((p for p in places if (p / "bin" / "archify.mjs").is_file()), None)


HELPER = Path(__file__).with_name("diagram.mjs")
_cache: dict[str, str] = {}


def draw(report: Report, threats: dict[str, Any], shape: str = "wide") -> str:
    """The diagram as a page fragment: one figure, CSS only, in the page's own colours.

    Drawn on request and kept in memory by what went into it, so an edited report is
    drawn again and an unchanged one is not."""
    job = {
        "candidate": candidate(report, threats, shape),
        "details": details(report, threats),
        "map": TOKENS,
        "idPrefix": f"keel-{shape}",
        "width": WIDTH[shape],
    }
    key = hashlib.sha256(json.dumps(job, sort_keys=True).encode()).hexdigest()
    if key in _cache:
        return _cache[key]
    node, home = shutil.which("node"), archify_dir()
    if not node or not home:
        raise Unavailable(
            "The diagram is drawn by Archify, which needs Node and the archify skill on this "
            "machine (set KEEL_ARCHIFY to its folder)."
        )
    with tempfile.TemporaryDirectory(prefix="keel-diagram-") as tmp:
        try:
            proc = subprocess.run(
                [node, str(HELPER), str(home), tmp], input=json.dumps(job), capture_output=True,
                text=True, encoding="utf-8", timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as e:
            raise Unavailable(f"Archify did not run: {e}") from e
    try:
        result = json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        raise Unavailable(f"Archify did not answer: {(proc.stderr or '').strip()[-400:]}") from None
    if result.get("status") != "pass":
        raise Unavailable(f"Archify refused the diagram: {result.get('message', 'no reason given')}")
    if len(_cache) > 64:
        _cache.clear()
    _cache[key] = result["html"]
    return result["html"]
