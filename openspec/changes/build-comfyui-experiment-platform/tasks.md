## 1. Application Foundation

- [x] 1.1 Choose and document the local web stack and initialize the backend, browser UI, test runner, and development commands.
- [x] 1.2 Define the local configuration layout, database schema, artifact directory layout, and migration strategy.
- [x] 1.3 Implement database and filesystem repositories for experiments, snapshots, artifacts, evaluations, scoring templates, AI analyses, and connection settings.
- [x] 1.4 Add application-level error handling, structured local logging, and a health endpoint without logging secrets.

## 2. AutoDL Connection

- [x] 2.1 Implement local-only storage and validation for one AutoDL connection, including host, port, username, key reference, remote root, and ComfyUI path settings.
- [x] 2.2 Implement SSH key permission checks and an actionable connection test for SSH access, remote root access, and ComfyUI workspace access.
- [x] 2.3 Build the connection settings UI with separate success and failure states for authentication, network, and remote-path problems.
- [x] 2.4 Add tests covering valid configuration, missing key, stopped/unreachable instance, authentication failure, and inaccessible remote paths.

## 3. Experiment Lifecycle

- [x] 3.1 Implement experiment creation with original-image upload, user goal, stable identifier, local artifact directory, and unique remote workspace path.
- [x] 3.2 Add UI for displaying the remote workspace path and the ComfyUI artifact conventions, including where to place inputs and save selected outputs.
- [x] 3.3 Implement experiment list, detail, status, snapshot history, and offline access to previously synchronized artifacts.
- [x] 3.4 Add tests for required original image validation, unique workspace creation, reopening experiments, and local access while AutoDL is unavailable.

## 4. Manual Synchronization and Metadata

- [x] 4.1 Define the remote artifact allowlist and temporary-file exclusion rules for inputs, masks, saved images, workflow JSON, and supported metadata.
- [x] 4.2 Implement SFTP directory inspection, stable-file checks, checksums, incremental download, and per-file transfer status.
- [x] 4.3 Implement immutable snapshot creation for successful, partial, retried, and empty synchronization results.
- [x] 4.4 Implement best-effort extraction of image-embedded metadata and workflow JSON fields, with unknown values and manual correction support.
- [x] 4.5 Build the manual sync UI with progress, ignored-file count, partial-failure details, retry action, and snapshot results.
- [x] 4.6 Add integration tests using a local SFTP fixture or test double for new files, changed files, ignored files, unstable files, retries, and repeated snapshots.

## 5. Candidate Comparison and Evaluation

- [x] 5.1 Implement candidate grouping by snapshot and image identity, including original-image and mask references when available.
- [x] 5.2 Build the comparison UI for multiple candidates with image viewing, source metadata, snapshot context, and evaluation state.
- [x] 5.3 Implement configurable quality dimensions, failure tags, template versioning, ordering, disabling, and historical-label preservation.
- [x] 5.4 Implement per-candidate evaluation with success/partial/failure status, 1-to-10 overall score, 1-to-10 dimension scores, tags, notes, incomplete-state handling, and editing.
- [x] 5.5 Add provenance fields and UI states that distinguish user-confirmed evaluation from AI suggestions.
- [x] 5.6 Add tests for failed and partial candidates, incomplete evaluations, custom dimensions, disabled historical dimensions, and multi-candidate comparison.

## 6. Multimodal Analysis

- [x] 6.1 Define a provider adapter for one configurable multimodal API, including request payloads for images, goal, workflow, metadata, and confirmed evaluation context.
- [x] 6.2 Implement local-only API credential handling, provider validation, timeout/error handling, and redacted logging.
- [x] 6.3 Implement explicit analysis requests for a candidate or comparison set; ensure synchronization does not trigger model calls.
- [x] 6.4 Implement storage for raw response, provider/model, request context, suggestions, draft status, confirmation, edits, rejection, and provenance.
- [x] 6.5 Build the AI analysis UI for request, loading/error states, editable suggestions, selective confirm/reject, and confirmed evaluation updates.
- [x] 6.6 Add tests for missing configuration, successful analysis, provider failure, unconfirmed drafts, edited confirmations, and rejected suggestions.

## 7. Verification and Documentation

- [x] 7.1 Add an end-to-end local workflow test covering create experiment, configure connection, sync a snapshot, compare candidates, score a failure, and save analysis.
- [x] 7.2 Document first-run setup, SSH key creation and AutoDL configuration, ComfyUI folder conventions, Save Image usage, manual sync, and third-party data disclosure.
- [x] 7.3 Document known limitations and the future extension points for automatic metadata extraction, workflow automation, additional instances, and training-data export.
- [x] 7.4 Run the full test suite and validate that all local artifacts, configuration files, and secrets are excluded from synchronization and logs.
