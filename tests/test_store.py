import pytest

from genesis.core.observation import Observation
from genesis.core.store import ObservationStore


def test_observation_rejects_empty_text():
    with pytest.raises(ValueError):
        Observation.create("   ")


def test_store_round_trip(tmp_path):
    store = ObservationStore(tmp_path / "test.sqlite3")
    original = Observation.create("What is programming?", source="test")
    store.add(original)

    assert store.count() == 1
    restored = store.list(limit=1)[0]
    assert restored == original
    assert list(store.all_texts()) == ["What is programming?"]


def test_store_limit_must_be_positive(tmp_path):
    store = ObservationStore(tmp_path / "test.sqlite3")
    with pytest.raises(ValueError):
        store.list(limit=0)
