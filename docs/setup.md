# First-run setup

dirtyLab is a local-only platform that helps you run, compare, and evaluate
ComfyUI experiments running on an AutoDL instance.

## 1. Install

Requirements: Python 3.11+ and Node 18+.

```bash
git clone <this repo>
cd dirtyLab
make install
```

This creates a Python venv, installs the backend as an editable package, and
installs the frontend dependencies.

## 2. First run

```bash
make dev
```

The backend listens on http://127.0.0.1:8000 and the frontend dev server on
http://127.0.0.1:5173. Open the frontend in your browser.

On first run, dirtyLab creates `./data/` next to the repo:

```
data/
  config.json          non-secret app config overrides
  secrets/             0600 files, never logged, never synced
    autodl_private_key   your AutoDL SSH private key
    provider_api_key     your multimodal provider API key
  dirtylab.db          SQLite database (experiments, snapshots, evaluations)
  artifacts/           synchronized images + metadata
    <experiment_id>/
      original.<ext>
      snapshots/<snapshot_id>/<kind>/<file>
```

`./data/` is gitignored and must never be committed.

## 3. Configure SSH access to AutoDL

1. On your local machine, generate a key pair (skip if you already have one):
   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/autodl_dirtylab -N ""
   ```
2. In the AutoDL web UI, add the contents of `~/.ssh/autodl_dirtylab.pub` to
   your SSH keys.
3. Start your AutoDL instance. Note the host, port, and username that AutoDL
   assigns.
4. In dirtyLab, open **AutoDL Connection**. Paste the contents of
   `~/.ssh/autodl_dirtylab` (the private key) into the form. Fill in host,
   port, username, and the remote experiment root (the directory that
   contains ComfyUI's `input/` and `output/`).
5. Click **Run test**. dirtyLab verifies SSH access, the remote root, and the
   ComfyUI workspace. The test reports each stage separately so an auth
   failure, a stopped instance, and a wrong remote path are all
   distinguishable.

The private key is written to `data/secrets/autodl_private_key` with mode
0600. dirtyLab never logs key material and never sends it anywhere.

## 4. ComfyUI folder conventions

Each experiment is given a unique remote workspace path under the remote
root: `<remote_root>/experiments/<experiment_id>/`. ComfyUI must be
configured to read inputs and write outputs from this directory.

Sync only transfers files from allowlisted subdirectories:

| Remote subdirectory | Artifact kind | Extensions |
| --- | --- | --- |
| `input/` (or `inputs/`) | input | `.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp` |
| `masks/` | mask | `.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp` |
| `output/` (or `outputs/`) | saved_image | `.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp` |
| `workflows/` | workflow_json | `.json` |

Everything else is reported as ignored.

### Save Image convention

Inside ComfyUI, every output worth keeping must go through a **Save Image**
node. The default Save Image filename prefix is `ComfyUI_`. You can change the
expected prefix in the AutoDL Connection settings; this does not change how
ComfyUI writes files — it just helps the connection test find the right
directory.

## 5. Multimodal provider

dirtyLab is pluggable. The default adapter speaks the OpenAI-compatible
`/chat/completions` API and works with OpenAI, Azure OpenAI, OpenRouter,
Together, vLLM, Ollama, and LM Studio. Open **AI Provider** to configure
the endpoint, model, and API key.

The API key is written to `data/secrets/provider_api_key` with mode 0600 and
is never logged, never synced, and never stored in experiment records.

### Third-party data disclosure

dirtyLab does **not** contact the provider during sync. The provider is only
called when you click **Request AI analysis** on a candidate. When you do,
the platform sends:

- the selected candidate image(s),
- the experiment goal,
- the available workflow JSON (excerpt),
- the extracted metadata summary, and
- (only if you opt in) confirmed evaluations on related candidates.

If you do not want any data to leave your machine, do not click that button
(or do not configure a provider at all).

## 6. Manual sync

Open an experiment and click **Sync now**. dirtyLab walks the remote
workspace over SFTP, transfers new or changed allowlisted files, and writes a
new immutable snapshot. Partial failures are reported with a retry button.
Sync is always manual — there is no polling.

## 7. Comparison and evaluation

Each synchronized `output/` image becomes a candidate. Candidates can be
scored on:

- result status (`success` / `partial_success` / `failure`),
- overall score (1-10),
- configurable quality dimensions (1-10),
- failure tags, and
- free-text notes.

Open **Scoring Template** to add, rename, disable, or reorder dimensions and
tags. Historical evaluations keep their original labels and scores intact
when the template changes.

## 8. AI analysis

From an experiment page, select one or more candidates and click **Request
AI analysis**. The provider returns failure causes, dimension scores, an
overall score, a status, and next-step suggestions. Each suggestion can be
edited, accepted, or rejected individually. Only confirmed values are
treated as ground-truth evaluation; the original AI suggestion is always
retained for provenance.
