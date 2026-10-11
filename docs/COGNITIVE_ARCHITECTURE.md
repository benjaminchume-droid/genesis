# Cognitive architecture: meaning, capabilities, and verified learning

Genesis now separates a request's inspectable goal frame from retrieved evidence and from final wording. The first implementation lives in `genesis.cognition.model`.

## Data flow

1. **Interpretation** produces a `GoalFrame`: utterance, intent cue, target, unresolved references and a conservative confidence value.
2. **World model** remains the persistent concept/relation graph. Parsed text is not automatically promoted to a trusted fact.
3. **Evidence and reasoning** select candidate propositions with provenance and epistemic status.
4. **Response planning** creates a `ResponsePlan` containing propositions and evidence IDs. Rendering is a separate later step.
5. **Capability registry** stores reusable procedure contracts, dependencies, constraints, implementation references, failure modes, and evaluation history. It stores skills and their contracts, not answer strings.
6. **Evaluation feedback** can promote a capability to `verified` only after an explicit passing evaluation without recorded regressions. A later failed evaluation returns it to `candidate`.

## Local API

- `GET /api/cognition/status`
- `POST /api/cognition/interpret` with `{"text":"Build a blue dog illustration"}`
- `GET /api/capabilities?q=parser&status=candidate`
- `POST /api/capabilities` with `{"operation":"register","name":"...","purpose":"...","inputs":[],"outputs":[]}`
- `POST /api/capabilities` with `{"operation":"evaluate","capability_id":"...","passed":true,"dataset_id":"heldout-v1","summary":"...","metrics":{},"regressions":[]}`

These endpoints use the existing loopback-only server. Capability registration is metadata only; it does not execute arbitrary code. A reference to an implementation is not proof that the implementation exists. The status field makes this distinction visible.

## What this does not claim

This is a foundational architectural change, not proof of top-model intelligence. Goal interpretation currently uses bounded surface cues; it is not a general semantic parser. The response-plan builder only organizes supplied claims and will not invent missing evidence. The capability registry does not synthesize new algorithms by itself. Generalization, language generation, project planning, and end-to-end task success still require dedicated implementations and independently held-out tests.

The intended long-term loop is:

`interpret goal -> build semantic representation -> consult world model and capabilities -> plan -> execute -> observe -> evaluate -> revise reusable capability -> regression-test`

Execution and persistent learning must remain separated: observations can suggest a hypothesis, but only evaluation and provenance can justify promoting it.
