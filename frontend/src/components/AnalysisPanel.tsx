import { useState } from "react";
import { api } from "../api/client";
import type { Analysis, Artifact } from "../api/types";

type Props = {
  experimentId: string;
  candidates: Artifact[];
  analyses: Analysis[];
  onChanged: () => void;
};

export function AnalysisPanel({ experimentId, candidates, analyses, onChanged }: Props) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [goalOverride, setGoalOverride] = useState("");
  const [includeComparison, setIncludeComparison] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function request() {
    setBusy(true);
    setErr(null);
    if (selectedIds.size === 0) {
      setErr("请先至少选择一个候选图。");
      setBusy(false);
      return;
    }
    try {
      await api.post(`/analyses/experiments/${experimentId}/request`, {
        artifact_ids: Array.from(selectedIds),
        goal_override: goalOverride || null,
        include_comparison_context: includeComparison,
      });
      setGoalOverride("");
      setSelectedIds(new Set());
      onChanged();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <p className="muted">
        选择一张或多张候选图，让模型根据目标、元数据和结果给出可编辑的建议。
      </p>
      {candidates.length > 0 ? (
        <div className="analysis-picker" aria-label="选择要分析的候选图">
          {candidates.map((candidate, index) => {
            const selected = selectedIds.has(candidate.id);
            return (
              <button
                className={`candidate-select ${selected ? "selected" : ""}`}
                key={candidate.id}
                type="button"
                aria-pressed={selected}
                onClick={() => {
                  const next = new Set(selectedIds);
                  if (selected) next.delete(candidate.id);
                  else next.add(candidate.id);
                  setSelectedIds(next);
                }}
              >
                <img
                  src={`/api/artifacts/${candidate.id}/file`}
                  alt={`候选图 ${index + 1}`}
                />
                <span className="candidate-select-copy">
                  <strong>候选图 {index + 1}</strong>
                  <small>{candidate.relative_path}</small>
                </span>
                <span className="selection-check" aria-hidden="true">
                  {selected ? "✓" : ""}
                </span>
              </button>
            );
          })}
        </div>
      ) : (
        <div className="empty-state compact">
          <span className="empty-icon" aria-hidden="true">✦</span>
          <span>同步候选图后，可以在这里请求 AI 分析。</span>
        </div>
      )}

      <div className="analysis-toolbar">
        <span className="selection-count">
          已选择 <strong>{selectedIds.size}</strong> / {candidates.length} 张
        </span>
        <button onClick={request} disabled={busy || selectedIds.size === 0}>
          {busy ? "请求中…" : "请求 AI 分析"}
        </button>
      </div>
      <div className="analysis-options">
        <label className="toggle-label">
          <input
            type="checkbox"
            checked={includeComparison}
            onChange={(e) => setIncludeComparison(e.target.checked)}
          />
          <span>带入其它已确认评分作为对比上下文</span>
        </label>
        <label>
          目标覆盖（可选）
          <input value={goalOverride} onChange={(e) => setGoalOverride(e.target.value)} />
        </label>
      </div>
      {err && <p className="error">{err}</p>}

      <ul className="list">
        {analyses.map((a) => (
          <li className="analysis-item" key={a.id}>
            <strong>
              {a.provider_kind} · {a.provider_model}
            </strong>
            <span className="muted">
              {" "}
              · {translateAnalysisStatus(a.status)} ·{" "}
              {new Date(a.requested_at).toLocaleString()}
            </span>
            {a.status === "success" && <AnalysisDetail analysis={a} onChanged={onChanged} />}
            {a.status === "failed" && <div className="error">{a.error_detail}</div>}
          </li>
        ))}
        {analyses.length === 0 && <li className="muted">还没有分析记录。</li>}
      </ul>
    </div>
  );
}

function AnalysisDetail({ analysis, onChanged }: { analysis: Analysis; onChanged: () => void }) {
  const suggestions = analysis.suggestions;
  const [edited, setEdited] = useState<{
    overall_score: number | "";
    status: NonNullable<Analysis["suggestions"]["status"]>;
    notes: string;
    rejected: string[];
  }>({
    overall_score: suggestions.overall_score ?? "",
    status: suggestions.status ?? "failure",
    notes: suggestions.failure_causes?.join("\n") ?? "",
    rejected: [],
  });
  const [confirmed, setConfirmed] = useState(analysis.is_confirmed);
  const [rejectedOnly, setRejectedOnly] = useState(analysis.is_rejected);

  async function submit(confirm: boolean) {
    const payload = confirm
      ? {
          overall_score: edited.overall_score === "" ? null : Number(edited.overall_score),
          status: edited.status,
          notes: edited.notes,
          rejected_fields: edited.rejected,
        }
      : { rejected_fields: edited.rejected };
    try {
      await api.post(`/analyses/${analysis.id}/confirm`, payload);
      if (confirm) {
        setConfirmed(true);
        setRejectedOnly(false);
      } else {
        setRejectedOnly(true);
      }
      onChanged();
    } catch (e) {
      alert((e as Error).message);
    }
  }

  function toggleReject(field: string) {
    const next = new Set(edited.rejected);
    if (next.has(field)) next.delete(field);
    else next.add(field);
    setEdited({ ...edited, rejected: Array.from(next) });
  }

  return (
    <div style={{ marginTop: 8 }}>
      <div className="muted">
        建议的失败原因：
        <ul>
          {(suggestions.failure_causes || []).map((c, i) => (
            <li key={i}>
              <label>
                <input
                  type="checkbox"
                  checked={!edited.rejected.includes(`failure_causes.${i}`)}
                  onChange={() => toggleReject(`failure_causes.${i}`)}
                />{" "}
                {c}
              </label>
            </li>
          ))}
        </ul>
      </div>
      <div className="grid">
        <label>
          总分（1-10）
          <input
            type="number"
            min={1}
            max={10}
            value={edited.overall_score}
            onChange={(e) =>
              setEdited({
                ...edited,
                overall_score: e.target.value === "" ? "" : Number(e.target.value),
              })
            }
          />
        </label>
        <label>
          结果
          <select
            value={edited.status}
            onChange={(e) =>
              setEdited({
                ...edited,
                status: e.target.value as NonNullable<Analysis["suggestions"]["status"]>,
              })
            }
          >
            <option value="success">成功</option>
            <option value="partial_success">部分成功</option>
            <option value="failure">失败</option>
          </select>
        </label>
      </div>
      <label>
        备注
        <textarea
          value={edited.notes}
          onChange={(e) => setEdited({ ...edited, notes: e.target.value })}
          rows={3}
        />
      </label>
      <div className="actions">
        <button onClick={() => submit(true)} disabled={confirmed}>
          {confirmed ? "已确认" : "确认（编辑后）"}
        </button>
        <button className="danger" onClick={() => submit(false)} disabled={rejectedOnly}>
          {rejectedOnly ? "已拒绝" : "全部拒绝"}
        </button>
      </div>
      {confirmed && (
        <span className="muted">已记为用户确认。原始建议保留作为溯源。</span>
      )}
    </div>
  );
}

function translateAnalysisStatus(s: string): string {
  switch (s) {
    case "pending":
      return "进行中";
    case "success":
      return "成功";
    case "failed":
      return "失败";
    default:
      return s;
  }
}
