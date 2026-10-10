# Safety, Privacy, and Execution Boundaries

## Local data

The initial CLI stores observations in a local SQLite database. Users must know where the file lives. Future releases need explicit retention, deletion, export, and sensitive-data handling controls before being described as production-ready.

Do not commit private conversation logs, credentials, personal records, or raw user datasets to the repository.

## External acquisition

Any future web retriever must record the source URL, retrieval time, relevant excerpt, and transformation history. Retrieved content is untrusted input. A webpage must not be allowed to issue commands to the runtime merely because Genesis is researching it.

## Code execution

Future procedure execution must be isolated, resource-limited, time-limited, and denied access to secrets by default. Generated code must be tested in a disposable environment before use. Tool permissions must be explicit.

## Self-modification

No autonomous self-modification is enabled in the initial foundation. Future architectural changes must be proposed, tested in isolation, reviewed against regression suites, versioned, and reversible. Changes to permissions, network access, data deletion, or execution policy require explicit authorization.

## Knowledge integrity

Keep observations, extracted claims, hypotheses, and verified results distinct. Preserve contradictory evidence. Do not treat user agreement, repetition, or source popularity as sufficient proof of truth.

## Supply chain

The initial runtime uses only the Python standard library. The development extra adds pytest for testing. Dependency additions must have a documented purpose and should not introduce neural inference or pretrained model dependencies.
