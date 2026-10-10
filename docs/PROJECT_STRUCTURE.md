# Project Structure

The repository is arranged by responsibility rather than by demo screen.

    genesis/
    ├── .github/
    │   └── workflows/
    │       └── tests.yml
    ├── docs/
    │   ├── ARCHITECTURE.md
    │   ├── DECISIONS.md
    │   ├── EVALUATION.md
    │   ├── INITIAL_STATUS.md
    │   ├── PROJECT_STRUCTURE.md
    │   ├── RESEARCH_PLAN.md
    │   ├── ROADMAP.md
    │   └── SAFETY_AND_SECURITY.md
    ├── src/
    │   └── genesis/
    │       ├── acquisition/
    │       │   └── source.py
    │       ├── capabilities/
    │       │   └── procedure.py
    │       ├── core/
    │       │   ├── evidence_store.py
    │       │   ├── observation.py
    │       │   └── store.py
    │       ├── dialogue/
    │       │   └── context.py
    │       ├── evaluation/
    │       │   └── dataset.py
    │       ├── interpretation/
    │       │   └── hypothesis.py
    │       ├── knowledge/
    │       │   └── claim.py
    │       ├── linguistics/
    │       │   └── surface.py
    │       ├── representations/
    │       │   └── relations.py
    │       ├── structures/
    │       │   └── discovery.py
    │       ├── __init__.py
    │       ├── __main__.py
    │       └── cli.py
    ├── tests/
    │   ├── test_claim_and_procedure.py
    │   ├── test_dataset_split.py
    │   ├── test_discovery.py
    │   ├── test_hypothesis.py
    │   ├── test_store.py
    │   └── test_surface.py
    ├── .gitignore
    ├── CONTRIBUTING.md
    ├── README.md
    └── pyproject.toml

## Module responsibilities

- core/observation.py defines the immutable record for a raw observation.
- core/store.py persists raw observations. It does not interpret them.
- core/evidence_store.py persists interpretation hypotheses and source-traceable claims while preserving their uncertain/unverified status.
- dialogue/context.py retains a bounded ordered window of recent turns; it does not infer their meanings.
- representations/relations.py stores generic relations and evidence references without imposing a fixed ontology.
- acquisition/source.py records source text, origin, acquisition time, and a content digest; it does not retrieve the web itself.
- linguistics/surface.py provides transparent segmentation and corpus statistics.
- structures/discovery.py identifies repeated token sequences and their left/right surface contexts. It does not assign meaning.
- interpretation/hypothesis.py defines an auditable hypothesis record; it does not infer intent.
- knowledge/claim.py defines source-traceable claim records; claims default to unverified.
- capabilities/procedure.py defines a procedure specification; it does not execute code.
- evaluation/dataset.py provides a deterministic split utility with exact-string deduplication.
- cli.py exposes the currently implemented operations.
- tests/ checks behavior of the current primitives.
- docs/ contains the roadmap, research protocol, evaluation criteria, architecture constraints, and truthful implementation status.

## Planned additions

The initial packages for candidate structure discovery, interpretation hypotheses, provenance-aware claim records, procedure specifications, and dataset splitting now exist. Concept representations, knowledge persistence, dialogue context, response planning, safe retrieval, execution isolation, and capability composition remain to be implemented. Add new modules only when their interfaces and tests are defined; do not create empty modules merely to make the tree appear complete.
