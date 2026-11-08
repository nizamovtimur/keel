"""The report drawn as a system diagram: who starts each risk, the parts of the system,
its trust boundary and the part each risk sits on, built from the report alone.

The picture is checked as data (boxes, arrows, colours by worst risk); the drawing
itself needs Node and Archify, so those tests run only where both are present.
"""
import shutil

import pytest
from fastapi.testclient import TestClient

import keel.config
from keel import diagram
from keel.main import app
from keel.schemas.report import Report
from tests.test_atlassian import HOSTILE, finding, report

THREATS = {
    "T-TOOL": {"title": "A tool acts on the model's say-so",
               "weaknesses": [{"component": "tool", "surface": ["model-output"]}]},
    "T-DOCS": {"title": "Poisoned documents", "weaknesses": [{"component": "knowledge-base", "surface": ["retrieved-content"]}]},
}


def rep(*findings, **over):
    return Report(**report(findings=list(findings), surfaces=[], discarded=[], **over))


def boxes(c):
    return {x["id"]: x for x in c["components"]}


def arrows(c):
    return {(x["from"], x["to"]) for x in c["connections"]}


def test_each_risk_sits_on_the_part_its_path_lands_on():
    r = rep(
        finding("T-TOOL", attack_surface="model-output", source={"who": "internal", "motive": "m", "access": "a"}),
        finding("T-DOCS", attack_surface="retrieved-content", risk={"likelihood": "low", "severity": "medium", "reasoning": "r"}),
        finding("T-CHAT", attack_surface="user-input", risk={"likelihood": "low", "severity": "low", "reasoning": "r"}),
    )
    c = diagram.candidate(r, THREATS)
    b = boxes(c)
    assert b["tool"]["type"] == "security"          # high, through the catalog's component
    assert b["knowledge-base"]["type"] == "messagebus"  # medium, on the part it comes in from
    assert b["system"]["type"] == "frontend"            # low, user input reaches the model itself
    assert {("system", "tool"), ("knowledge-base", "system"),
            ("who-external-attacker", "knowledge-base"), ("who-internal", "system")} <= arrows(c)


def test_severity_is_said_in_words_as_well_as_colour():
    c = diagram.candidate(rep(finding("T-TOOL", attack_surface="model-output")), THREATS)
    assert boxes(c)["tool"]["sublabel"] == "1 risk · high"
    assert boxes(c)["system"]["sublabel"] == "no risk found"
    assert boxes(c)["who-external-attacker"]["sublabel"] == "starts 1 risk"


def test_the_trust_boundary_holds_the_system_and_not_who_starts_the_risks():
    c = diagram.candidate(rep(finding("T-DOCS", attack_surface="retrieved-content")), THREATS)
    wraps = set(c["boundaries"][0]["wraps"])
    assert wraps == {"system", "knowledge-base"}
    assert "who-external-attacker" in boxes(c)


def test_the_models_own_failures_have_no_box_outside():
    c = diagram.candidate(rep(finding("T-A", source={"who": "model-mistake", "motive": "m", "access": "a"})), THREATS)
    assert not [x for x in c["components"] if x["type"] == "external"]


def test_a_ledger_row_carries_the_risks_its_outcome_names():
    r = Report(**report(surfaces=[
        {"id": "S1", "kind": "tool", "name": "issue_refund", "where": "tools/refund.py", "outcome": ["T-A"]},
        {"id": "S2", "kind": "data", "name": "orders", "where": "db", "note": "read only"},
    ]))
    b = boxes(diagram.candidate(r, THREATS))
    assert b["s-s1"]["type"] == "security" and b["s-s2"]["type"] == "backend"
    assert b["system"]["sublabel"] == "no risk found"
    assert diagram.details(r, THREATS)["s-s2"] == "read only"


def test_a_long_name_is_cut_on_the_box_and_whole_in_its_card():
    r = rep(finding("T-A"), system_name="The customer support assistant of the year")
    assert len(boxes(diagram.candidate(r, THREATS))["system"]["label"]) <= diagram.LABEL_MAX
    assert "The customer support assistant of the year" in diagram.details(r, THREATS)["system"]


def test_report_text_reaches_the_card_as_text():
    r = rep(finding("T-NEW", scenario=HOSTILE + ". More."), system_id="demo")
    card = diagram.details(r, {})["system"]
    assert "<script>" not in card and "&lt;script&gt;" in card
    assert 'href="/reports/demo/2026-11-07/T-NEW"' in card


def test_both_shapes_hold_the_same_boxes():
    r = rep(finding("T-TOOL", attack_surface="model-output"), finding("T-DOCS", attack_surface="retrieved-content"))
    wide, narrow = (diagram.candidate(r, THREATS, s) for s in ("wide", "narrow"))
    assert set(boxes(wide)) == set(boxes(narrow))
    assert {x["col"] for x in narrow["components"]} == {0}
    assert {x["col"] for x in wide["components"] if x["type"] == "external"} == {0}


def test_a_part_read_and_written_is_one_box():
    th = {"T-W": {"weaknesses": [{"component": "memory", "surface": ["model-output"]}]}}
    r = rep(finding("T-R", attack_surface="memory"), finding("T-W", attack_surface="model-output"))
    c = diagram.candidate(r, th)
    assert boxes(c)["memory"]["sublabel"] == "2 risks · high"
    assert len([x for x in c["connections"] if {x["from"], x["to"]} == {"memory", "system"}]) == 1


def test_without_node_or_archify_the_page_is_told_why(monkeypatch, tmp_path):
    monkeypatch.setenv("KEEL_ARCHIFY", str(tmp_path))
    with pytest.raises(diagram.Unavailable, match="KEEL_ARCHIFY"):
        diagram.draw(rep(finding("T-Z")), THREATS)


def test_route_says_why_when_it_cannot_draw(tmp_path, monkeypatch):
    import yaml

    monkeypatch.setattr(keel.config.settings, "reports_dir", str(tmp_path))
    monkeypatch.setenv("KEEL_ARCHIFY", str(tmp_path / "none"))
    (tmp_path / "demo").mkdir()
    (tmp_path / "demo" / "2026-11-07.yaml").write_text(yaml.safe_dump(report(system_id="demo")), encoding="utf-8")
    c = TestClient(app)
    body = c.get("/api/reports/demo/2026-11-07/diagram").json()
    assert body["html"] is None and "Archify" in body["reason"]
    assert c.get("/api/reports/demo/2026-11-08/diagram").status_code == 404
    assert c.get("/api/reports/demo/2026-11-07/diagram?shape=round").status_code == 422


# Everything a report can hold at once: every source, every channel, every landing part.
WHO = ["external-attacker", "supply-chain", "internal", "error", "accident", "model-mistake"]
CHANNELS = ["user-input", "retrieved-content", "tool-output", "agent-message", "memory", "training-data", None]
LANDING = ["tool", "downstream", "identity-store", "config", "memory", "knowledge-base"]


def crowded() -> tuple[Report, dict]:
    threats, fs = {}, []
    for i, who in enumerate(WHO):
        for j, ch in enumerate(CHANNELS):
            fs.append(finding(f"T-{i}-{j}", attack_surface=ch, source={"who": who, "motive": "m", "access": "a"}))
    for k, comp in enumerate(LANDING):
        threats[f"T-OUT-{k}"] = {"weaknesses": [{"component": comp, "surface": ["model-output"]}]}
        fs.append(finding(f"T-OUT-{k}", attack_surface="model-output"))
    return rep(*fs), threats


@pytest.mark.skipif(not (shutil.which("node") and diagram.archify_dir()), reason="needs Node and Archify")
@pytest.mark.parametrize("shape", ["wide", "narrow"])
def test_archify_passes_the_drawing_of_a_crowded_report(shape):
    r, threats = crowded()
    html = diagram.draw(r, threats, shape)
    assert html.startswith("<figure") and "<script" not in html


def test_a_defect_is_named_in_plain_words_and_is_not_the_model():
    c = diagram.candidate(rep(finding("T-A", source={"who": "error", "motive": "m", "access": "a"})), THREATS)
    assert boxes(c)["who-error"]["label"] == "Bug or bad setup"
