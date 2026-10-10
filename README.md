# Genesis

Genesis is a research project investigating a non-neural cognitive architecture that acquires linguistic capability through experience, structural discovery, hypothesis testing, and reusable knowledge construction.

The long-term objective is a system that can interpret what a person means, respond usefully, investigate unknown topics, and acquire new capabilities without neural networks, pretrained neural weights, or a conventional neural-network training pipeline.

## Non-negotiable design constraints

- **No neural networks.** No neural-network inference, embeddings, or hidden model dependency.
- **No pretrained weights.** The runtime must not require downloaded model weights.
- **Primitive rule.** Build general-purpose mechanisms that perform real work. Avoid simulated intelligence, canned demo paths, and hard-coded answers disguised as understanding.
- **Evidence before claims.** Separate observed evidence, hypotheses, learned representations, and verified procedures.
- **Generalization matters.** A capability is not demonstrated merely because a stored example can be repeated.
- **Small-machine development.** Keep the initial runtime compatible with modest machines, targeting an 8 GB RAM development environment.
- **Inspectable change.** Acquired knowledge and executable procedures must be traceable, testable, versioned, and reversible.

## Important scope boundary

Genesis is a research program, not a claim that human-level language understanding has already been solved. The first code foundation implements an inspectable, non-neural observation and structural-discovery substrate. It does **not** yet provide human-level natural-language understanding. A tokenizer, word-frequency table, or co-occurrence pattern is not semantic comprehension.

The central research challenge is to discover whether general-purpose non-neural mechanisms can acquire useful linguistic interpretation from experience without quietly replacing that challenge with a manually authored English rule system.

## Initial research loop

1. Observe language without assuming it is understood.
2. Preserve the observation and its provenance.
3. Discover candidate structures from repeated evidence.
4. Construct competing interpretations or hypotheses.
5. Test them against new observations and outcomes.
6. Retain validated knowledge with uncertainty and provenance.
7. Compose acquired capabilities to handle unfamiliar tasks.
8. Measure transfer, error correction, and regressions.

## Repository status

**Stage:** foundational architecture and research scaffold.

The initial implementation is intentionally modest: a local SQLite observation store, a Unicode-aware surface segmenter, and frequency-based structural observations. These are instruments for experimentation, not an intelligent conversational agent. Semantic interpretation, intent inference, grounded concepts, response planning, web acquisition, and capability composition remain research milestones.

## Quick start

Requires Python 3.11 or newer. The initial foundation uses only the Python standard library.

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1

python -m pip install -e ".[dev]"
genesis observe "The dog chased the cat."
genesis stats
pytest
```

Alternatively, without installing the package:

```bash
python -m genesis observe "The dog chased the cat."
```

The CLI stores observations locally in `.genesis/genesis.sqlite3` unless `GENESIS_HOME` points elsewhere. Do not feed it private data unless you understand and accept that local storage behavior.

## Repository map

- `src/genesis/core/`: observation and persistence primitives.
- `src/genesis/linguistics/`: surface-level text processing and structural statistics.
- `tests/`: behavioral tests for implemented primitives.
- `docs/ARCHITECTURE.md`: component boundaries and data flow.
- `docs/ROADMAP.md`: staged implementation roadmap.
- `docs/RESEARCH_PLAN.md`: research questions, experiments, and falsification criteria.
- `docs/EVALUATION.md`: benchmark principles and evaluation protocol.
- `docs/SAFETY_AND_SECURITY.md`: execution, privacy, and self-modification boundaries.
- `docs/DECISIONS.md`: architectural decisions and trade-offs.

## Guiding rule

Every claim about understanding must be backed by a reproducible test on unfamiliar examples. Fluent output alone is not evidence of understanding.