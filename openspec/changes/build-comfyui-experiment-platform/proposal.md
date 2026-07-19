## Why

ComfyUI can produce many useful experiments, but failed generations, workflow changes, masks, and evaluation results are difficult to preserve as one coherent record. This change introduces a local experiment platform so image-editing attempts can be compared, scored, and accumulated into reliable knowledge before any future automation or model training.

## What Changes

- Add local experiment creation with an original image and a unique experiment workspace.
- Add one AutoDL connection configured through a locally stored SSH key, with connection diagnostics.
- Synchronize selected artifacts from an AutoDL/ComfyUI experiment workspace on demand, with repeatable snapshots.
- Preserve generated candidates, selected intermediate images, workflow JSON, masks, and available metadata.
- Add side-by-side candidate comparison and per-candidate evaluation using result status, overall satisfaction, configurable 1-to-10 quality dimensions, failure tags, and notes.
- Add manually triggered multimodal-model analysis that proposes failure causes, scores, and next-step suggestions.
- Allow users to edit and confirm AI analysis before it becomes part of the experiment record.
- Keep all experiment records and third-party API credentials on the local machine.
- Keep ComfyUI as the workspace for masking, workflow editing, and generation; the platform does not replace its editor or automatically modify workflows in the first version.

## Capabilities

### New Capabilities

- `local-experiment-management`: Create, organize, snapshot, and review local image-generation experiments.
- `autodl-comfyui-sync`: Configure one AutoDL instance and manually synchronize selected ComfyUI artifacts over SSH.
- `candidate-evaluation`: Compare multiple output candidates and record structured, editable human evaluations.
- `multimodal-analysis`: Request, review, edit, confirm, and persist analysis from a third-party multimodal model.

### Modified Capabilities

None.

## Impact

- Adds a local web application and local persistence for experiments, snapshots, evaluations, and configuration.
- Integrates with one remote AutoDL instance through SSH/SFTP and the ComfyUI filesystem/output conventions.
- May read ComfyUI workflow and image metadata when available; metadata extraction is best-effort and remains manually correctable.
- Integrates with one configurable third-party multimodal-model API while keeping API credentials local.
- Introduces no change to ComfyUI itself and no automatic model training or workflow execution in the first version.
