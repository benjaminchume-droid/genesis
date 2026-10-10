from genesis.linguistics.surface import segment, summarize


def test_segment_preserves_word_order_and_punctuation():
    assert segment("The dog chased the cat.") == [
        "The", "dog", "chased", "the", "cat", "."
    ]


def test_segment_supports_unicode_and_apostrophes():
    assert segment("Ça va? don't stop!") == [
        "Ça", "va", "?", "don't", "stop", "!"
    ]


def test_summarize_counts_tokens_and_pairs():
    result = summarize(["a b", "a b c"])
    assert result.observation_count == 2
    assert result.token_count == 5
    assert result.unique_token_count == 3
    assert result.frequent_tokens[0] == ("a", 2)
    assert result.adjacent_pairs[0] == (("a", "b"), 2)


def test_summarize_empty_corpus():
    result = summarize([])
    assert result.observation_count == 0
    assert result.token_count == 0
    assert result.unique_token_count == 0
