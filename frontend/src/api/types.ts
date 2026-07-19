// Shared API response types.

export interface Connection {
  id: string;
  host: string;
  port: number;
  username: string;
  private_key_ref: string;
  remote_root: string;
  comfyui_input_path: string;
  comfyui_output_prefix: string;
  last_test_status: string | null;
  last_test_at: string | null;
  last_test_detail: string | null;
}

export interface ConnectionTestResult {
  ok: boolean;
  stage: "ssh_access" | "remote_root" | "comfyui_input" | "comfyui_output";
  detail: string | null;
  resolved_paths: Record<string, string> | null;
}

export interface Provider {
  id: string;
  kind: string;
  label: string;
  base_url: string;
  model: string;
  api_key_ref: string;
}

export interface ExtractedMetadata {
  field_name: string;
  field_value: string;
  is_unknown: boolean;
  is_user_corrected: boolean;
}

export interface Artifact {
  id: string;
  snapshot_id: string;
  relative_path: string;
  kind: string;
  checksum: string;
  size_bytes: number;
  transfer_status: string;
  error_detail: string | null;
  extracted_metadata: ExtractedMetadata[];
}

export interface Snapshot {
  id: string;
  experiment_id: string;
  number: number;
  status: string;
  source_path: string;
  ignored_count: number;
  error_detail: string | null;
  started_at: string;
  finished_at: string | null;
  created_at: string;
  artifacts: Artifact[];
}

export interface Experiment {
  id: string;
  name: string;
  goal: string;
  original_filename: string;
  original_extension: string;
  original_checksum: string;
  remote_workspace_path: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ExperimentDetail extends Experiment {
  snapshots: Snapshot[];
  evaluations: Evaluation[];
  analyses: Analysis[];
}

export interface Dimension {
  id: string;
  key: string;
  label: string;
  order_index: number;
  is_disabled: boolean;
}

export interface Tag {
  id: string;
  key: string;
  label: string;
  order_index: number;
  is_disabled: boolean;
}

export interface Template {
  id: string;
  version: number;
  is_active: boolean;
  created_at: string;
  dimensions: Dimension[];
  tags: Tag[];
}

export interface Evaluation {
  id: string;
  artifact_id: string;
  status: "success" | "partial_success" | "failure";
  overall_score: number | null;
  notes: string;
  is_complete: boolean;
  provenance: "human" | "ai_confirmed" | "ai_edited";
  template_version: number;
  dimension_scores: { key: string; label: string; score: number | null }[];
  tags: { key: string; label: string }[];
  created_at: string;
  updated_at: string;
}

export interface Analysis {
  id: string;
  experiment_id: string;
  provider_kind: string;
  provider_model: string;
  status: "pending" | "success" | "failed";
  error_detail: string | null;
  suggestions: Record<string, unknown>;
  is_confirmed: boolean;
  is_rejected: boolean;
  confirmed_overall_score: number | null;
  confirmed_status: string | null;
  confirmed_notes: string;
  requested_at: string;
  completed_at: string | null;
  confirmed_at: string | null;
}

export interface SyncResult {
  snapshot: Snapshot;
  partial_failures: { path: string; reason: string }[];
  ignored_count: number;
  retryable: boolean;
}
