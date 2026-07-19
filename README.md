# dirtyLab

A local experiment platform for ComfyUI image-editing workflows on AutoDL. Create
experiments, configure one AutoDL SSH connection, manually sync ComfyUI artifacts
as immutable snapshots, compare candidates, record human evaluations, and request
editable multimodal AI analysis.

## Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy + SQLite, Paramiko (SFTP), pytest
- **Frontend:** Vite + React + TypeScript
- **AI provider:** pluggable adapter; default reference is an OpenAI-compatible
  chat/completions endpoint that accepts image inputs

See [docs/setup.md](docs/setup.md) for first-run setup and
[docs/limitations.md](docs/limitations.md) for known limitations.

## Quick start

```bash
# from repo root
make install        # create venv, install backend + frontend deps
make dev            # run backend (8000) and frontend (5173) together
make test           # run pytest + frontend typecheck/tests
make lint           # ruff + mypy + eslint
```

Backend dev server: http://127.0.0.1:8000
Frontend dev server: http://127.0.0.1:5173

All experiment data, snapshots, and credentials stay on the local machine under
`./data` (configurable). See `docs/setup.md`.
