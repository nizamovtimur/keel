"""`keel site`: the read-only HTML copy published to GitHub or GitLab Pages.

What matters here is what may reach a published page: no report unless asked, no draft
unless asked again, no markup from a record, no script, and no link that leads nowhere.
"""
import re
import shlex
from pathlib import Path

import pytest
import yaml

from keel import site
from keel.store import Store, set_store

REPO = Path(__file__).resolve().parent.parent

REPORT = {
    "system_id": "checkout-agent",
    "system_name": "Checkout Agent",
    "system_description": "Handles checkout for the storefront.",
    "date": "2026-08-26",
    "assessor": "Jane Doe <jane@example.com>",
    "status": "final",
    "findings": [{
        "id": "T-ONE",
        "from_catalog": True,
        "scenario": "A user plants <script>alert(1)</script> in a ticket.",
        "source": {"who": "external-attacker", "motive": "steal", "access": "any user"},
        "asset": "orders",
        "attack_surface": "retrieved-content",
        "vulnerability": "lookups are not scoped",
        "exploitation_complexity": "low",
        "harm": "data-exposed",
        "risk": {"likelihood": "medium", "severity": "high",
                 "reasoning": "Any user can plant the text."},
        "delta": "New with the assistant.",
        "requirements": [{"mitigation_id": "CTRL-ONE",
                          "coverage_status": "needs_implementation"}],
    }],
    "discarded": [{"id": "T-TWO", "reason": "nothing runs the output"}],
}


@pytest.fixture
def catalog(catalog_dir):
    d = catalog_dir(
        threats=[
            {"id": "T-ONE", "mitigations": [
                {"id": "CTRL-ONE", "strength": "gating", "rationale": "blocks it"}]},
            {"id": "T-TWO", "title": "Second <b>threat</b>"},
        ],
        mitigations=[{"id": "CTRL-ONE"}],
    )
    set_store(Store(d))
    yield d
    set_store(None)


def _reports(tmp_path, *docs):
    root = tmp_path / "reports"
    for doc in docs:
        folder = root / doc["system_id"]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{doc['date']}.yaml").write_text(yaml.safe_dump(doc), encoding="utf-8")
    return root


def _pages(out):
    return {p.relative_to(out).as_posix(): p.read_text(encoding="utf-8")
            for p in out.rglob("*.html")}


def test_catalog_pages_and_every_link_resolves(catalog, tmp_path):
    out = tmp_path / "public"
    reports = _reports(tmp_path, REPORT)
    site.build_site(out, reports)
    pages = _pages(out)
    for rel in ("index.html", "threats/T-ONE/index.html", "mitigations/CTRL-ONE/index.html",
                "coverage/index.html", "reports/checkout-agent/2026-08-26/index.html"):
        assert rel in pages
    for rel, text in pages.items():
        for href in re.findall(r'href="([^"#]+)', text):
            if href.startswith("http"):
                continue
            target = (out / rel).parent / href
            assert target.is_file(), f"{rel} links to {href}, which is not built"


def test_no_report_without_the_flag(catalog, tmp_path):
    _reports(tmp_path, REPORT)
    out = tmp_path / "public"
    site.build_site(out)
    assert not (out / "reports" / "checkout-agent").exists()


def test_drafts_only_when_asked(catalog, tmp_path):
    draft = dict(REPORT, system_id="draft-agent", status="draft")
    reports = _reports(tmp_path, REPORT, draft)
    out = tmp_path / "public"
    site.build_site(out, reports)
    assert not (out / "reports" / "draft-agent").exists()
    site.build_site(out, reports, include_drafts=True)
    assert (out / "reports" / "draft-agent" / "2026-08-26" / "index.html").is_file()


def test_report_whose_content_disagrees_with_its_path_is_skipped(catalog, tmp_path):
    reports = _reports(tmp_path, REPORT)
    (reports / "checkout-agent" / "2026-08-26.yaml").rename(
        reports / "checkout-agent" / "2026-09-01.yaml")
    out = tmp_path / "public"
    assert site.build_site(out, reports)["reports"] == 0


def test_record_text_is_escaped_and_pages_carry_no_script(catalog, tmp_path):
    out = tmp_path / "public"
    site.build_site(out, _reports(tmp_path, REPORT))
    for rel, text in _pages(out).items():
        assert "<script" not in text, rel
        assert "<b>threat</b>" not in text, rel
        assert 'http-equiv="Content-Security-Policy"' in text, rel
        assert "default-src 'none'" in text, rel


def test_refuses_a_folder_it_did_not_build_and_clears_its_own(catalog, tmp_path):
    foreign = tmp_path / "docs"
    foreign.mkdir()
    (foreign / "keep.txt").write_text("mine", encoding="utf-8")
    with pytest.raises(SystemExit):
        site.build_site(foreign)
    assert (foreign / "keep.txt").is_file()

    out = tmp_path / "public"
    site.build_site(out)
    stale = out / "threats" / "T-GONE" / "index.html"
    stale.parent.mkdir(parents=True)
    stale.write_text("old", encoding="utf-8")
    site.build_site(out)
    assert not stale.exists()


@pytest.mark.parametrize("path", ["examples/pages/github-pages.yml",
                                  "examples/pages/gitlab-ci.yml"])
def test_example_pipelines_call_the_real_command(path):
    """The CI examples are copied into other people's repos; a flag that does not exist
    would fail there, not here."""
    doc = yaml.safe_load((REPO / path).read_text(encoding="utf-8"))

    def strings(node):
        if isinstance(node, dict):
            for v in node.values():
                yield from strings(v)
        elif isinstance(node, list):
            for v in node:
                yield from strings(v)
        elif isinstance(node, str):
            yield node

    calls = [s for s in strings(doc) if "keel site" in s]
    assert calls, f"{path} does not run keel site"
    for call in calls:
        argv = shlex.split(call.split("keel site", 1)[1])
        site.parser().parse_args(argv)
