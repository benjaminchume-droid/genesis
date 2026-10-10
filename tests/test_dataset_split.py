from genesis.evaluation.dataset import deterministic_split


def test_split_is_deterministic_and_deduplicates_exact_examples():
    examples = [f"example {i}" for i in range(100)] + ["example 1"]
    first = deterministic_split(examples)
    second = deterministic_split(examples)
    assert first == second
    all_items = first.discovery + first.development + first.held_out
    assert len(all_items) == len(set(examples))
    assert first.dataset_fingerprint


def test_split_rejects_invalid_fractions():
    import pytest

    with pytest.raises(ValueError):
        deterministic_split(["a", "b"], discovery_fraction=0.8, development_fraction=0.3)
