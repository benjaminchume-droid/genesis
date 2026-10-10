import pytest

from genesis.dialogue.context import DialogueContext, DialogueTurn


def test_dialogue_context_keeps_recent_turns_in_order():
    context = DialogueContext(max_turns=2)
    first = DialogueTurn.create("user", "first")
    second = DialogueTurn.create("assistant", "second")
    third = DialogueTurn.create("user", "third")

    context.append(first)
    context.append(second)
    context.append(third)

    assert context.turns() == (second, third)


def test_dialogue_context_validates_capacity_and_turns():
    with pytest.raises(ValueError):
        DialogueContext(max_turns=0)
    with pytest.raises(ValueError):
        DialogueTurn.create("user", " ")
