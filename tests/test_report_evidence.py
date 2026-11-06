"""Open questions block, evidence is an addendum, and evidence links are safe.

An assessment must not go past a fact it has not established: a question gets an answer
before the branch that needs it is graded, and the report cannot be finalized while one
is open. Claims point at an evidence list instead of carrying their proof in the prose,
and a link in that list is model output, so it is held to a pinned, allowlisted shape.
"""

import pytest
import yaml

import keel.config
from keel.errors import Invalid
from keel.schemas.report import Evidence, OpenQuestion
from keel.services import report_service
from keel.store import Store, set_store

SHA = "4043f65a1b2c3d4e5f60718293a4b5c6d7e8f901"

READ = {"id": 1, "kind": "read", "commit": SHA, "path": "app/refunds.py", "lines": "40-52",
        "quote": "def refund(order_id, amount):\n    return gateway.refund(order_id, amount)"}


def _finding(**over):
    f = {
        "id": "T-A",
        "from_catalog": True,
        "scenario": "A customer asks for a refund and the bot issues it with no check [1].",
        "source": {"who": "external-attacker", "motive": "money", "access": "the chat"},
        "asset": "refunds",
        "attack_surface": "user-input",
        "vulnerability": "the refund tool takes the amount from the model",
        "exploitation_complexity": "low",
        "harm": "data-exposed",
        "risk": {"likelihood": "high", "severity": "high", "reasoning": "Anyone can ask."},
        "delta": "new: the refund tool came with the bot",
        "evidence": [1],
    }
    f.update(over)
    return f


def _report(**over):
    r = {
        "system_id": "demo", "system_name": "Demo", "system_description": "A system.",
        "date": "2026-11-06", "assessor": "Tester <t@example.com>", "status": "draft",
        "findings": [_finding()], "evidence": [dict(READ)],
    }
    r.update(over)
    return r


@pytest.fixture
def archive(catalog_dir, tmp_path, monkeypatch):
    d = catalog_dir(threats=[
        {"id": "T-A", "harm": "data-exposed", "source": ["external-attacker", "internal"]},
        {"id": "T-B"},
    ])
    set_store(Store(d))
    reports = tmp_path / "reports"
    (reports / "demo").mkdir(parents=True)
    monkeypatch.setattr(keel.config.settings, "reports_dir", str(reports))
    monkeypatch.setattr(keel.config.settings, "evidence_hosts", ["git.example.internal"])
    yield reports
    set_store(None)


def _save(reports, payload):
    (reports / "demo" / "2026-11-06.yaml").write_text(
        yaml.safe_dump(_report(findings=[]), sort_keys=False), encoding="utf-8")
    return report_service.save_report("demo", "2026-11-06", payload)


def _messages(exc):
    return " | ".join(d["message"] for d in exc.value.details)


# --- evidence entries ------------------------------------------------------------- #

def test_a_read_points_at_lines_at_a_commit():
    with pytest.raises(ValueError, match="lines"):
        Evidence(**{**READ, "lines": None})
    with pytest.raises(ValueError):
        Evidence(**{**READ, "commit": "main"})  # a branch is not a pin


def test_a_command_needs_what_was_run():
    with pytest.raises(ValueError, match="command"):
        Evidence(id=2, kind="command", quote="HTTP/1.1 200 OK")
    Evidence(id=2, kind="command", quote="HTTP/1.1 200 OK", command="curl -si localhost:8080/admin")


def test_the_quote_is_required():
    with pytest.raises(ValueError):
        Evidence(**{**READ, "quote": ""})


def test_a_question_says_where_the_assessor_looked():
    with pytest.raises(ValueError):
        OpenQuestion(id="Q1", question="Is the admin endpoint exposed?", needed_for="T-B, step 9")
    q = OpenQuestion(id="Q1", question="Read access to the ingress config?", asks_for="access",
                     looked_in="Not in this repository; it lives in the platform repo",
                     needed_for="T-B, step 9")
    assert q.answer is None


# --- save: links hold together ------------------------------------------------------- #

def test_a_well_formed_report_saves_and_has_nothing_open(archive):
    result = _save(archive, _report())
    assert result["success"] and result["open"] == []


def test_a_finding_citing_missing_evidence_is_refused(archive):
    with pytest.raises(Invalid) as exc:
        _save(archive, _report(findings=[_finding(evidence=[1, 7])]))
    assert "evidence 7" in _messages(exc)


def test_duplicate_evidence_ids_are_refused(archive):
    with pytest.raises(Invalid):
        _save(archive, _report(evidence=[dict(READ), dict(READ)]))


@pytest.mark.parametrize("url", [
    "http://git.example.internal/r/blob/%s/app/refunds.py#L40-L52" % SHA,     # not https
    "https://evil.example.com/r/blob/%s/app/refunds.py#L40-L52" % SHA,        # host not allowed
    "https://git.example.internal/r/blob/main/app/refunds.py#L40-L52",       # a branch, not the commit
    "https://git.example.internal/r/blob/%s/app/refunds.py" % SHA,            # no line anchor
    "https://git.example.internal/r/blob/%s/app/refunds.py?d=secret#L40" % SHA,  # carries data
    "https://u:p@git.example.internal/r/blob/%s/app/refunds.py#L40" % SHA,     # credentials
])
def test_an_unsafe_evidence_link_is_refused(archive, url):
    with pytest.raises(Invalid) as exc:
        _save(archive, _report(evidence=[{**READ, "url": url}]))
    assert "evidence[0]" in _messages(exc)


def test_a_pinned_link_on_an_allowed_host_is_kept(archive):
    url = "https://git.example.internal/r/blob/%s/app/refunds.py#L40-L52" % SHA
    result = _save(archive, _report(evidence=[{**READ, "url": url}]))
    assert result["report"]["evidence"][0]["url"] == url


def test_no_host_is_allowed_by_default(archive, monkeypatch):
    monkeypatch.setattr(keel.config.settings, "evidence_hosts", [])
    url = "https://github.com/o/r/blob/%s/app/refunds.py#L40-L52" % SHA
    with pytest.raises(Invalid):
        _save(archive, _report(evidence=[{**READ, "url": url}]))


# --- open questions block ------------------------------------------------------------ #

Q_OPEN = {"id": "Q1", "question": "Is the admin endpoint reachable from the internet?",
          "looked_in": "The service code binds 0.0.0.0; the ingress config is not in this repo",
          "needed_for": "T-B, reachability", "asks_for": "access"}
PAUSED = {"id": "T-B", "from_catalog": True, "waiting_on": ["Q1"],
          "note": "The endpoint has no auth; whether it is reachable decides the grade."}


def test_a_paused_branch_is_reported_as_open(archive):
    result = _save(archive, _report(open_questions=[Q_OPEN], paused=[PAUSED]))
    assert any("Q1" in m for m in result["open"])
    assert any("T-B" in m for m in result["open"])


def test_a_paused_branch_must_wait_on_a_question_that_exists(archive):
    with pytest.raises(Invalid) as exc:
        _save(archive, _report(paused=[PAUSED]))
    assert "Q1" in _messages(exc)


def test_an_answered_question_does_not_leave_its_branch_waiting(archive):
    answered = {**Q_OPEN, "answer": "Yes, it is behind the public load balancer."}
    with pytest.raises(Invalid) as exc:
        _save(archive, _report(open_questions=[answered], paused=[PAUSED]))
    assert "no longer waits" in _messages(exc)


def test_a_threat_is_paused_or_decided_never_both(archive):
    with pytest.raises(Invalid):
        _save(archive, _report(open_questions=[Q_OPEN],
                               paused=[{**PAUSED, "id": "T-A"}]))


def test_finalize_refuses_while_anything_is_open(archive):
    _save(archive, _report(open_questions=[Q_OPEN], paused=[PAUSED]))
    with pytest.raises(Invalid) as exc:
        report_service.finalize_report("demo", "2026-11-06")
    assert "Q1" in _messages(exc)


def test_finalize_refuses_a_finding_with_no_evidence(archive):
    _save(archive, _report(findings=[_finding(evidence=[])]))
    with pytest.raises(Invalid) as exc:
        report_service.finalize_report("demo", "2026-11-06")
    assert "no evidence" in _messages(exc)


def test_finalize_goes_through_once_everything_is_established(archive):
    answered = {**Q_OPEN, "answer": "Yes, it is behind the public load balancer."}
    b = _finding(id="T-B", harm="data-exposed")
    _save(archive, _report(open_questions=[answered], findings=[_finding(), b]))
    assert report_service.finalize_report("demo", "2026-11-06")["report"]["status"] == "final"


# --- advice: harm and source against the catalog threat ------------------------------ #

def test_a_harm_outside_the_threat_is_said_out_loud(archive):
    result = _save(archive, _report(findings=[_finding(harm="reputation-legal")]))
    assert any("reputation-legal" in a for a in result["advice"])


def test_a_source_outside_the_threat_is_said_out_loud(archive):
    f = _finding(source={"who": "model-mistake", "motive": "a long ticket", "access": "the tool"})
    result = _save(archive, _report(findings=[f]))
    assert any("model-mistake" in a for a in result["advice"])


def test_advice_never_blocks_the_save(archive):
    result = _save(archive, _report(findings=[_finding(harm="reputation-legal")]))
    assert result["success"]


# --- the rest of the finding ---------------------------------------------------------- #

def test_attack_surface_may_be_empty_where_the_weakness_has_none(archive):
    result = _save(archive, _report(findings=[_finding(attack_surface=None)]))
    assert result["report"]["findings"][0]["attack_surface"] is None


def test_deployment_is_its_own_field(archive):
    result = _save(archive, _report(findings=[_finding(deployment="off")]))
    assert result["report"]["findings"][0]["deployment"] == "off"
    with pytest.raises(Invalid):
        _save(archive, _report(findings=[_finding(deployment="maybe")]))


def test_a_fingerprint_needs_a_root_cause():
    assert report_service.fingerprint("demo", "T-A", None) is None
    assert report_service.fingerprint("demo", "T-A", "refund-amount-from-model") == \
        "demo/T-A/refund-amount-from-model"


def test_an_old_report_without_the_new_parts_still_reads(archive):
    old = _report()
    for k in ("evidence",):
        old.pop(k)
    old["findings"] = [{k: v for k, v in _finding().items() if k != "evidence"}]
    (archive / "demo" / "2026-11-06.yaml").write_text(yaml.safe_dump(old), encoding="utf-8")
    got = report_service.get_report("demo", "2026-11-06")
    assert got["report"]["findings"][0]["evidence"] == []
