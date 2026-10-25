"""The store notices when someone else changes the catalog.

The MCP server and the UI are two processes over the same files. Each used to serve the
copy it loaded at startup, so a threat written through one did not exist in the other
until it was restarted.
"""
import pytest
import yaml

from keel import store as store_module
from keel.store import Store, get_store, set_store


@pytest.fixture
def served(catalog_dir, monkeypatch):
    """A catalog installed as the process-wide store, with the check not rationed, so a
    test does not have to sleep to get past the interval."""
    monkeypatch.setattr(store_module, "_FRESHNESS_INTERVAL", 0)
    directory = catalog_dir(threats=[{"id": "T-A"}], mitigations=[{"id": "CTRL-A"}])
    set_store(Store(directory))
    yield directory
    set_store(None)


def _threat(threat_id, **extra):
    return {
        "id": threat_id,
        "title": threat_id,
        "harm": "data-exposed",
        "weaknesses": [{"component": "tool", "text": "no scoping on lookups"}],
        "reachability": "the model never sees anything worth taking",
        **extra,
    }


def test_a_file_added_by_another_process_is_served(served):
    assert list(get_store().threats) == ["T-A"]
    (served / "threats" / "T-B.yaml").write_text(
        yaml.safe_dump(_threat("T-B"), sort_keys=False), encoding="utf-8"
    )
    assert sorted(get_store().threats) == ["T-A", "T-B"]


def test_a_file_edited_by_another_process_is_served(served):
    (served / "threats" / "T-A.yaml").write_text(
        yaml.safe_dump(_threat("T-A", title="Renamed elsewhere"), sort_keys=False),
        encoding="utf-8",
    )
    assert get_store().threats["T-A"]["title"] == "Renamed elsewhere"


def test_a_file_deleted_by_another_process_stops_being_served(served):
    (served / "mitigations" / "CTRL-A.yaml").unlink()
    assert get_store().mitigations == {}


def test_the_stores_own_write_does_not_reload_it(served):
    store = get_store()
    store.threats["T-A"]["title"] = "Renamed here"
    store.write_threat("T-A")
    assert store.refresh_if_changed() is False


def test_nothing_changed_means_no_reload(served):
    assert get_store().refresh_if_changed() is False


def test_someone_elses_change_survives_our_own_write(served):
    """Restamping after a write covers the written file only. Restamping everything
    would mark a change made elsewhere in the same moment as already seen."""
    store = get_store()
    (served / "threats" / "T-B.yaml").write_text(
        yaml.safe_dump(_threat("T-B"), sort_keys=False), encoding="utf-8"
    )
    store.mitigations["CTRL-A"]["name"] = "Renamed here"
    store.write_mitigation("CTRL-A")
    assert store.refresh_if_changed() is True
    assert "T-B" in store.threats
    assert store.mitigations["CTRL-A"]["name"] == "Renamed here"
