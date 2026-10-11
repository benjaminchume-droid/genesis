# Genesis cognitive architecture

This document records the current implementation boundary and the architecture imported as a design reference from Gene-X. It is not a claim that Genesis has Gene-X's full capabilities.

## Design principle

Genesis separates four things that must not collapse into a stored question/answer pair:

1. **Experience:** what happened, when, in what context, and what result followed.
2. **Knowledge:** claims and relations with source, confidence, and epistemic status.
3. **Procedure:** reusable capability contracts and ordered operations that can apply across instances.
4. **Expression:** a structured plan of propositions and evidence that a language realizer can express.

A recalled episode may inform a new answer, but it is not itself the answer. A world-model assertion may be a hypothesis, not a fact. A capability description is not executable functionality until an implementation and evaluation exist.

## Gene-X architecture inspected as reference

The reference exploration covered Gene-X's repository tree (585 entries) and core modules including:

- `gene/brain/cognitive.py`, `cycle.py`, `representation.py`
- `gene/cognition/kernel.py`, `reasoning.py`, `planning.py`
- `gene/language/interpreter.py`, `representation.py`, `response.py`, `realization.py`
- `gene/world/model.py`, `inference.py`, `causality.py`
- `gene/memory/store.py`, `episodic.py`, `semantic.py`, `procedural.py`
- `gene/learning/engine.py`, `generalization.py`
- `gene/runtime/learning_loop.py`
- `gene/capabilities/registry.py`, `mcp.py`
- `gene/code/project.py`, `ast.py`, `generation.py`, `verification.py`
- `gene/tasks/graph.py`

The tree also contains multimodal, model-provider, execution, training, release, security and benchmark subsystems. These are separate implementations and were not all ported or independently audited line-by-line.

## Implemented in Genesis in this change set

### Persistent world model

`genesis.world.model.WorldModel` stores entities, attributes, relations/properties, events, source provenance, evidence identifiers, confidence and epistemic status in SQLite. Contradictory assertions remain visible. The model never treats persistence as proof.

`WorldReasoner` composes two explicitly supported relation edges into a **hypothesis**, preserving premise identifiers and reducing confidence. This is bounded graph reasoning, not a general causal simulator.

### Persistent multi-store memory

`PersistentMemory` separates episodic, semantic, procedural, working and general memory records. It stores update/retrieval events and supports transparent BM25-like lexical retrieval. Episode consolidation only proposes candidates; it does not silently promote them into facts.

This is not vector-semantic retrieval, human-like memory, or automatic abstraction. Those require measurable evaluation and stronger representations.

### Meaning-first cognitive cycle

`CognitiveCycle` orchestrates:

1. record the new observation;
2. analyze linguistic surface cues;
3. form an inspectable goal frame;
4. retrieve relevant past experiences and world assertions;
5. expose contradictions and missing evidence;
6. optionally run bounded browser research;
7. return an evidence-linked response plan with uncertainty and next-step metadata.

It does not just return the last answer associated with a matching question. However, the language parser remains bounded and the returned plan is not yet a general fluent language generator.

### Compositional response realization

`genesis.dialogue.realization` can realize an explicit subject/predicate/object frame into new surface wording, preserve polarity and limited modality, and carry evidence identifiers into the response. This avoids looking up a stored answer string for supported structured frames. It does not yet paraphrase arbitrary prose fluently; when no semantic frame exists, it preserves source text rather than pretending to understand it.

### Dependency-aware planning primitives

`genesis.cognition.planning.TaskPlan` validates a bounded dependency graph, exposes ready steps, tracks attempts and results, retries within an explicit budget, and blocks dependent steps after permanent failure. Plan steps refer to registered capabilities; they are data and cannot contain arbitrary executable source. This is a planning substrate, not a complete natural-language goal-to-plan synthesizer.

### Reusable capability registry

Capabilities are persisted with input/output contracts, dependencies, implementation references, constraints, failure modes and evaluation history. They remain candidates until a passing evaluation is recorded; a later failure demotes them. Registration does not turn metadata into executable code.

### Local API

New routes:

- `GET /api/world`, `GET /api/world/conflicts`
- `POST /api/world/assertions`, `POST /api/world/events`
- `GET /api/memory?q=...`, `POST /api/memory`, `POST /api/memory/consolidate`
- `POST /api/cognition/cycle`, `POST /api/cognition/realize`
- `GET /api/capabilities`, `POST /api/capabilities`

The API retains the existing loopback-only server boundary. Do not expose this server directly to the public internet.

## Still not implemented by this change

- A robust general-purpose semantic-role parser or reliable pronoun/coreference resolution.
- A fast, broad, open-ended natural-language realization engine.
- A learned world-transition/causal simulator that predicts unfamiliar situations accurately.
- A general goal-to-plan synthesizer that can safely create unfamiliar projects without supplied plan structures.
- General code generation, compiler/toolchain orchestration, sandboxed execution, patch/repair loops and project-scale verification.
- GPU training, a neural foundation model, or demonstrated model-scale language competence.
- Vector retrieval or independently evaluated semantic memory.
- Full Gene-X MCP capability parity, multimodal perception/generation, distributed training, or complete benchmark suite.
- Production qualification. CI and device installation tests must pass on the final commit, and functional quality requires held-out benchmarks.

## Verification contract

The added tests cover persistence, provenance, contradiction visibility, bounded relation composition, cognitive-cycle output, memory retrieval, and local API integration. CI results are the authority for whether the current commit passes the automated suite. A green suite proves only those tested behaviors, not general intelligence or production readiness.
