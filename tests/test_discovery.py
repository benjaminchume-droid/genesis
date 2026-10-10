from genesis.structures.discovery import discover_repeated_sequences


def test_discovery_finds_repeated_sequence_and_context():
    report = discover_repeated_sequences(
        [
            "the dog chased the cat",
            "the dog chased the ball",
            "the cat chased the dog",
        ],
        min_length=2,
        max_length=2,
        min_occurrences=2,
    )
    candidate = next(item for item in report.candidates if item.tokens == ("the", "dog"))
    assert candidate.occurrences == 3
    assert candidate.observation_indices == (0, 1, 2)
    assert ("chased", 2) in candidate.right_contexts


def test_discovery_is_case_insensitive_by_default():
    report = discover_repeated_sequences(
        ["Hello there", "hello there"],
        min_length=2,
        max_length=2,
    )
    assert report.candidates[0].tokens == ("hello", "there")
    assert report.candidates[0].occurrences == 2


def test_discovery_validates_bounds():
    import pytest

    with pytest.raises(ValueError):
        discover_repeated_sequences(["a"], min_length=3, max_length=2)
