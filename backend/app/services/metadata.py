"""Best-effort metadata extraction (Task 4.4).

We try to recover prompt, workflow, model, seed, and generation fields from
both PNG chunks (ComfyUI/A1111 conventions) and workflow JSON sidecars. When a
field is absent we store an ``unknown`` row rather than inferring from an
unrelated file.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image
from sqlalchemy.orm import Session

from app.models import Artifact
from app.services import experiment_repo


KNOWN_FIELDS = ["prompt", "workflow", "model", "seed", "steps", "sampler", "cfg"]


def extract_and_store(
    db: Session, artifact: Artifact, local_path: str | Path, *, kind: str
) -> None:
    path = Path(local_path)
    fields: dict[str, tuple[str, bool]] = {}
    if kind in {"saved_image", "input", "mask"} and path.suffix.lower() == ".png":
        fields.update(_extract_png(path))
    if kind == "workflow_json":
        fields.update(_extract_workflow_json(path))
    # Ensure every known field has an explicit row so the UI can mark it
    # unknown instead of guessing.
    for name in KNOWN_FIELDS:
        if name in fields:
            value, is_unknown = fields[name]
        else:
            value, is_unknown = "", True
        experiment_repo.upsert_extracted_metadata(
            db,
            artifact_id=artifact.id,
            field_name=name,
            field_value=value,
            is_unknown=is_unknown,
        )


def _extract_png(path: Path) -> dict[str, tuple[str, bool]]:
    out: dict[str, tuple[str, bool]] = {}
    try:
        with Image.open(path) as img:
            info = getattr(img, "info", {}) or {}
            prompt = info.get("prompt") or info.get("parameters")
            if isinstance(prompt, str) and prompt:
                out["prompt"] = (prompt, False)
            workflow = info.get("workflow")
            if isinstance(workflow, str) and workflow:
                out["workflow"] = (workflow, False)
            # Common A1111-style keys.
            for key, target in (
                ("Model", "model"),
                ("Seed", "seed"),
                ("Steps", "steps"),
                ("Sampler", "sampler"),
                ("CFG scale", "cfg"),
            ):
                value = info.get(key)
                if value:
                    out[target] = (str(value), False)
    except Exception:  # best-effort
        pass
    return out


def _extract_workflow_json(path: Path) -> dict[str, tuple[str, bool]]:
    out: dict[str, tuple[str, bool]] = {}
    try:
        data: Any = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return out
    if isinstance(data, dict):
        # ComfyUI workflow exports vary; grab anything obvious.
        for key in ("prompt", "model", "seed", "steps", "sampler", "cfg"):
            if key in data:
                out[key] = (json.dumps(data[key])[:4096], False)
        if "workflow" in data:
            out["workflow"] = (json.dumps(data["workflow"])[:4096], False)
    return out
