from genesis.runtime.service import GenesisRuntime


def test_world_model_persists_provenance_and_reports_conflicts(tmp_path):
    db = tmp_path / "world.sqlite3"
    world = GenesisRuntime(tmp_path).world
    first = world.assert_claim("water", "state", "liquid", confidence=0.9,
        status="supported", source="source-a", evidence=["doc-1"])
    second = world.assert_claim("water", "state", "solid", confidence=0.4,
        status="hypothesis", source="source-b")
    assert first["evidence"] == ["doc-1"]
    assert first["status"] == "supported"
    conflicts = world.contradictions(subject="water", predicate="state")
    assert len(conflicts) == 1
    assert {conflicts[0]["value_a"], conflicts[0]["value_b"]} == {"liquid", "solid"}
    reopened = type(world)(db)
    assert reopened.status()["assertions"] == 0  # separate database remains isolated
    same = type(world)(tmp_path / "world.sqlite3")
    assert same.status()["assertions"] == 2


def test_world_relation_composition_is_hypothesis_only(tmp_path):
    runtime = GenesisRuntime(tmp_path)
    runtime.world.assert_claim("Lagos", "located_in", "Nigeria", kind="relation",
        object_is_entity=True, status="supported", confidence=0.95, source="source-a")
    runtime.world.assert_claim("Nigeria", "located_in", "Africa", kind="relation",
        object_is_entity=True, status="supported", confidence=0.9, source="source-b")
    results = runtime.world_reasoner.compose_relations(
        first_predicate="located_in", second_predicate="located_in",
        composed_predicate="located_in")
    assert any(x.subject == "Lagos" and x.value == "Africa" for x in results)
    result = next(x for x in results if x.subject == "Lagos" and x.value == "Africa")
    assert result.epistemic_status == "hypothesis"
    assert len(result.premises) == 2


def test_cognitive_cycle_returns_inspectable_frame_and_evidence_gap(tmp_path):
    runtime = GenesisRuntime(tmp_path)
    result = runtime.cognitive_cycle.run("What is a verb?")
    assert result["goal_frame"]["act"]
    assert "linguistic_analysis" in result
    assert result["response_plan"]["propositions"] == []
    assert "not proof" in result["response_plan"]["uncertainty"] or "evidence gap" in result["response_plan"]["uncertainty"]
    assert runtime.status()["world_model"]["world"]["assertions"] == 0


def test_world_api_accepts_claims_and_reports_conflicts():
    import json
    from threading import Thread
    from urllib.request import Request, urlopen
    from genesis.server import serve

    server = serve(host="127.0.0.1", port=0, home=None, background=True)
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        payload = json.dumps({"subject":"tea","predicate":"temperature","value":"hot",
            "status":"supported","confidence":0.9,"source":"test"}).encode()
        req = Request(base + "/api/world/assertions", data=payload, headers={"Content-Type":"application/json"})
        with urlopen(req, timeout=3) as response:
            assert response.status == 201
            assert json.load(response)["subject_label"] == "tea"
        with urlopen(base + "/api/world?subject=tea", timeout=3) as response:
            body = json.load(response)
            assert body["status"]["assertions"] == 1
            assert body["assertions"][0]["object_value"] == "hot"
    finally:
        server.shutdown()
        server.server_close()
