# Known limitations and extension points

dirtyLab v1 is intentionally small. The following are known limitations and
the planned extension points for future versions.

## Limitations

- **One AutoDL instance.** Only one SSH connection is supported. Multi-instance
  support is deferred.
- **No instance lifecycle.** dirtyLab does not start or stop AutoDL instances
  and never asks for AutoDL account API credentials. Start your instance in
  the AutoDL web UI before configuring the connection.
- **No workflow automation.** dirtyLab never submits or modifies ComfyUI
  workflows. You drive ComfyUI as usual and use dirtyLab to capture the
  results.
- **Manual sync only.** dirtyLab does not poll the remote workspace and does
  not call the AI provider on sync. All transfers and all model calls are
  explicit.
- **Best-effort metadata.** ComfyUI's image metadata depends on workflow
  configuration and Save Image node settings. dirtyLab parses PNG chunks
  (`prompt`, `workflow`, common A1111 keys) and workflow JSON sidecars, and
  labels every unknown field explicitly so you can correct it manually. No
  inferred values are produced from unrelated files.
- **No automatic metadata extraction for exotic formats.** WebP, BMP, and
  JPEG do not carry ComfyUI-style chunks in the same way PNG does; metadata
  for those formats is limited to workflow JSON sidecars.
- **Single user, local-only.** The platform is designed for one local user.
  All data lives under `data/`; there is no remote database.

## Extension points

- **Automatic metadata extraction.** Add new extractors under
  `app/services/metadata.py`. Extractors are best-effort and must always
  store an explicit `unknown` row for any field they could not recover.
- **Workflow automation.** The platform does not submit workflows in v1.
  Future versions could add a workflow-runner service that writes to the
  remote `workflows/` directory and triggers a sync; the data model already
  records workflow JSON as artifacts.
- **Additional AutoDL instances.** `Connection` rows have an `is_active` flag
  and a unique-by-active constraint is enforced in the API. Supporting
  multiple active connections is a matter of relaxing the upsert rule in
  `connection_repo.upsert_connection` and exposing a picker in the UI.
- **Additional providers.** Implement the `MultimodalProvider` Protocol in
  `app/providers/__init__.py` and register it in `get_provider`. The data
  model already stores `provider_kind` and `provider_model` on each analysis
  so multiple providers can coexist.
- **Training-data export.** The data model links experiments, snapshots,
  artifacts, evaluations (with provenance), and AI analyses. A future export
  job could materialize a curated dataset (e.g. only user-confirmed
  successful candidates) without schema changes.

## Operational notes

- **Deleting an experiment** removes its local artifacts directory and all
  related snapshots, evaluations, and analyses. The remote workspace on
  AutoDL is never touched by dirtyLab.
- **Rollback** is performed by deleting `./data/`. The first run recreates
  the layout and seeds a default scoring template.
- **Logs** are written to stdout in a redacted form (see
  `safe_join_for_log`). Known secret keys are replaced with `***` before
  logging. If you log additional fields, route them through that helper.
