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
    │       ├── core/
    │       │   ├── observation.py
    │       │   └── store.py
    │       ├── linguistics/
    │       │   └── surface.py
    │       ├── __init__.py
    │       ├── __main__.py
    │       └── cli.py
    ├── tests/
    │   ├── test_store.py
    │   └── test_surface.py
    ├── .gitignore
    ├── CONTRIBUTING.md
    ├── README.md
    └── pyproject.toml

## Module responsibilities

- core/observation.py defines the immutable record for a raw observation.
- core/store.py persists observations. It does not interpret them.
- linguistics/surface.py provides a transparent surface segmentation baseline and corpus statistics.
- cli.py exposes the currently implemented operations.
- tests/ checks behavior of the current primitives.
- docs/ contains the roadmap, research protocol, evaluation criteria, architecture constraints, and truthful implementation status.

## Planned additions

The roadmap may add separate packages for candidate structure discovery, interpretation hypotheses, concept representations, provenance-aware knowledge, capability composition, and evaluation harnesses. Add these only when their interfaces and tests are defined. Avoid creating empty modules merely to make the tree appear complete.
