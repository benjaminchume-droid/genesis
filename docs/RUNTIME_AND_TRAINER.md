# Genesis Runtime and Trainer

## Learning cycle

1. The local runtime persists observations, task checkpoints and installed knowledge releases on-device.
2. The user reviews and generalizes a learning item. Raw conversations are not automatic contribution inputs.
3. Explicit export includes only records marked consented, generalized and public, with evidence/provenance and content hashes.
4. Trainer ingestion validates each unique record and places it in quarantine. It never publishes automatically.
5. A reviewer accepts or rejects quarantined records. Release assembly includes accepted records only.
6. The client verifies package structure and hashes, installs a version immutably, and can activate or roll back to an installed version.

## Commands

Install the repository with python -m pip install -e ., then run genesis-workspace --help.

- genesis-workspace status
- genesis-workspace task-create "Investigate a topic and retain evidence"
- genesis-workspace task-checkpoint TASK_ID --status running --progress 0.2 --data JSON_OBJECT
- genesis-workspace contribution-export --input reviewed.jsonl --output contributions.jsonl
- genesis-workspace trainer-ingest contributions.jsonl
- genesis-workspace trainer-list --status quarantined
- genesis-workspace trainer-review CONTENT_HASH --decision accepted --reason "Evidence independently checked"
- genesis-workspace release-build --version 0.1.0 --output genesis-0.1.0.gmodel
- genesis-workspace release-verify genesis-0.1.0.gmodel
- genesis-workspace model-install genesis-0.1.0.gmodel

Each contribution input line is a JSON object matching LearningContribution. It must include explicit consent, generalized=true, sensitivity=public, and evidence or a provenance reference. This is an eligibility contract, not proof personal data has been removed. Review content before export; software cannot reliably identify every secret or personal detail.

## Guarantees and gaps

- Release packages contain manifest.json and knowledge.jsonl. SHA-256 hashes detect corruption and accidental modification.
- Hashes do not authenticate the publisher. Publisher signatures, trusted key rotation, remote update metadata and delta packages are not implemented; do not treat untrusted packages as authenticated.
- Trainer acceptance is an explicit human review state. The current trainer does not resolve semantic contradictions or independently establish truth.
- Installed packages are immutable by version name; activation is atomic and previous versions remain available for rollback.
- The package stores structured contributions. It is not a neural model or general-purpose natural-language generator. Existing grounded learning remains a narrow token/outcome association experiment.
- No automatic network upload, hosted trainer server, update polling, Android APK, Windows installer, or Linux desktop package exists yet. Shared lifecycle and schemas are implemented as Python services/CLI first so native clients can share one contract.
