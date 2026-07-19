import { useState } from "react";
import { api } from "../api/client";
import type { Analysis } from "../api/types";

interface Props {
  experimentId: string;
  analyses: Analysis[];
  onChanged: () => void;
}

export function AnalysisPanel({ experimentId, analyses, onChanged }: Props) {
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
        选中候选图后点击请求。同步时绝不会触发 AI 调用——只有这个按钮会。
      </p>
      <button onClick={request} disabled={busy}>
        {busy ? "请求中…" : "请求 AI 分析"}
      </button>
      <label>
        <input
          type="checkbox"
          checked={includeComparison}
          onChange={(e) => setIncludeComparison(e.target.checked)}
        />{" "}
        包含对比上下文（同实验下其它已确认评分）
      </label>
      <label>
        目标覆盖（可选）
        <input value={goalOverride} onChange={(e) => setGoalOverride(e.target.value)} />
      </label>
      {err && <p className="error">{err}</p>}

      <ul className="list">
        {analyses.map((a) => (
          <li key={a.id}>
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
  const suggestions = analysis.suggestions as Record<string, any>;
  const [edited, setEdited] = useState({
    overall_score: suggestions.overall_score ?? "",
    status: suggestions.status ?? "failure",
    notes: Array.isArray(suggestions.failure_causes)
      ? suggestions.failure_causes.join("\n")
      : "",
    rejected: [] as string[],
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
          {(suggestions.failure_causes || []).map((c: string, i: number) => (
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
            onChange={(e) => setEdited({ ...edited, status: e.target.value })}
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
