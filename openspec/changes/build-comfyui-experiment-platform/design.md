## Context

The project starts as an empty repository and serves one user on a local machine. ComfyUI runs on one manually started AutoDL instance and remains the user's workspace for loading images, drawing masks, editing workflows, and generating outputs. The local platform is an experiment ledger around that workflow: it creates experiment records, identifies a remote experiment directory, synchronizes explicitly saved artifacts on demand, stores immutable snapshots, and supports comparison and review.

The design must preserve useful failure data without requiring a second image editor or a fully automated workflow runner. The remote connection is the main boundary: the local service needs SSH/SFTP access, but it does not need to install software on AutoDL or alter ComfyUI in the first version.

## Goals / Non-Goals

**Goals:**

- Provide a local browser UI for creating and reviewing experiments.
- Configure and test one AutoDL SSH connection using a locally stored key.
- Give every experiment a stable local identity and a corresponding remote workspace.
- Synchronize selected ComfyUI artifacts manually and preserve each sync as a snapshot.
- Make candidate comparison and structured human evaluation fast enough for repeated experiments.
- Let a user request multimodal analysis, edit the result, and distinguish AI suggestions from confirmed observations.
- Keep the data model extensible for later automatic metadata extraction, workflow automation, and training-data export.

**Non-Goals:**

- Reimplementing ComfyUI's workflow or mask editor.
- Automatically starting or stopping AutoDL instances.
- Automatically submitting workflows or changing their parameters.
- Periodic background synchronization in the first version.
- Supporting multiple AutoDL instances.
- Training or fine-tuning an image model.

## Decisions

### Local service with browser UI

Use a local application with a small backend API, browser UI, local database, and filesystem artifact store. Keep experiment metadata in SQLite (or an equivalent embedded relational store) and keep binary files on disk, linked by records and checksums. This keeps the first deployment single-user and offline-friendly while allowing later UI and automation growth.

Alternative considered: a spreadsheet or Markdown-only ledger. Rejected because candidate comparison, repeated snapshots, structured scoring, and AI review need stable relationships and interactive state.

### SSH/SFTP as the AutoDL boundary

Use SSH key authentication and SFTP-compatible file operations for connection tests, directory listing, file upload, and file download. Store the private key path or a locally generated key reference in local configuration; never include private key material in experiment records or synchronized data. The first version requires the user to start AutoDL and configure the remote ComfyUI workspace.

Alternative considered: AutoDL account API integration. Deferred because it would add instance lifecycle credentials and is unnecessary when the user starts the instance manually.

### Explicit remote workspace and manual synchronization

Each experiment receives a unique remote directory beneath a configured experiment root. The UI shows the directory path and the artifact conventions to use in ComfyUI. The user performs all ComfyUI operations and uses `Save Image` nodes for outputs worth retaining. A manual sync compares the remote directory with the local manifest, downloads new or changed allowlisted files, parses available metadata, and writes a new immutable snapshot. The sync operation is repeatable and does not overwrite an earlier snapshot.

Alternative considered: polling the remote directory. Deferred because it complicates lifecycle, network usage, and partial-file handling without improving the initial workflow.

### Artifact allowlist and best-effort metadata

Sync only the experiment's input, mask, workflow, saved image, and explicitly supported metadata/log files. Ignore temporary previews, caches, and unrelated files unless the user marks them for inclusion. Parse image-embedded metadata and workflow JSON when available, but retain the original files and allow manual correction when extraction is incomplete.

Alternative considered: download every file under the ComfyUI output directory. Rejected because temporary and unrelated generations would pollute experiments and increase transfer size.

### Snapshot-oriented data model

Model an experiment as a long-lived container with ordered snapshots. Each snapshot records the sync time, source paths, checksums, transfer status, and the artifacts discovered in that sync. Candidate images belong to a snapshot but evaluations remain editable and persist independently, so later scoring does not mutate the original synchronized files.

### Human-confirmed evaluation and AI assistance

Represent human ratings, failure tags, notes, and AI suggestions as separate but linked records. The UI supports success, partial success, and failure; an overall 1-to-10 score; configurable quality dimensions; and free-text notes. A manual AI request sends only the selected experiment context and images to one configured multimodal API. The response is stored as an editable draft. The user can accept, modify, or reject each suggestion; only confirmed content is treated as the user's evaluation.

Alternative considered: automatic AI scoring on every sync. Rejected because it would increase API cost, make accidental uploads likely, and remove the user's control over when analysis is meaningful.

## Risks / Trade-offs

- [ComfyUI path conventions vary by workflow] → Make the remote root, experiment directory, input path, and output filename prefix visible and configurable; document the required `Save Image` convention and report files found outside it.
- [ComfyUI may not embed all execution metadata] → Preserve original images and workflow JSON, parse metadata best-effort, expose missing fields for manual entry, and never pretend an unavailable value was recovered.
- [A sync may encounter files still being written] → Use file-size/mtime stability checks, checksums, and a per-file transfer status; allow the user to retry the sync.
- [SSH credentials can expose the AutoDL instance] → Use key authentication, local-only secret storage, restrictive file permissions, connection diagnostics, and no credential values in logs.
- [Third-party multimodal analysis sends private images outside the machine] → Make the request explicit, show the selected payload, require a configured API key, and record provider/model metadata without storing the secret.
- [Scores may be inconsistent across time] → Keep the scoring template version and raw user notes with each evaluation; allow dimensions to be changed without rewriting old scores.

## Migration Plan

There is no existing application or data to migrate. The first run creates local configuration, database tables, artifact directories, and an empty scoring template. Failure or rollback is handled by deleting the local application data; remote experiment folders remain untouched unless the user explicitly removes them.

## Open Questions

- Which concrete local web stack and packaging format should be used during implementation?
- Which third-party multimodal API should be supported first?
- Should the first version provide a guided setup for configuring ComfyUI's remote input/output paths, or only display the required paths?
