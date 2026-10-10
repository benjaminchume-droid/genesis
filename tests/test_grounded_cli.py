import json

from genesis.cli import main


def test_learn_evaluate_cli_reports_baselines(tmp_path, capsys):
    train = tmp_path / "train.jsonl"
    test = tmp_path / "test.jsonl"
    train.write_text(
        '{"text":"dax red","label":"warm"}\n'
        '{"text":"dax bright","label":"warm"}\n'
        '{"text":"wug blue","label":"cool"}\n'
        '{"text":"wug dim","label":"cool"}\n',
        encoding="utf-8",
    )
    test.write_text(
        '{"text":"dax blue","label":"warm"}\n'
        '{"text":"wug bright","label":"cool"}\n',
        encoding="utf-8",
    )

    assert main(["learn-evaluate", "--train", str(train), "--test", str(test)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["learner"]["accuracy"] == 1.0
    assert set(output["baselines"]) == {"majority", "exact_retrieval", "token_frequency"}
