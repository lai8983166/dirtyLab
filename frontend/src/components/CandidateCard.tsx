import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Artifact, Evaluation, Template } from "../api/types";

interface Props {
  artifact: Artifact;
  template: Template | null;
  onChanged: () => void;
}

export function CandidateCard({ artifact, template, onChanged }: Props) {
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [status, setStatus] = useState<Evaluation["status"]>("failure");
  const [overall, setOverall] = useState<number | "">("");
  const [notes, setNotes] = useState("");
  const [scores, setScores] = useState<Record<string, number | "">>({});
  const [selectedTags, setSelectedTags] = useState<Set<string>>(new Set());
  const [isComplete, setIsComplete] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.get<Evaluation | null>(`/evaluations/artifacts/${artifact.id}`).then((e) => {
      if (!e) return;
      setEvaluation(e);
      setStatus(e.status);
      setOverall(e.overall_score ?? "");
      setNotes(e.notes);
      setIsComplete(e.is_complete);
      const next: Record<string, number | ""> = {};
      e.dimension_scores.forEach((d) => {
        next[d.key] = d.score ?? "";
      });
      setScores(next);
      setSelectedTags(new Set(e.tags.map((t) => t.key)));
    });
  }, [artifact.id]);

  async function save(provenance: Evaluation["provenance"] = "human") {
    if (!template) {
      setErr("没有可用的评分模板。");
      return;
    }
    setErr(null);
    const payload = {
      status,
      overall_score: overall === "" ? null : overall,
      notes,
      is_complete: isComplete,
      provenance,
      dimension_scores: template.dimensions
        .filter((d) => !d.is_disabled)
        .map((d) => ({ key: d.key, label: d.label, score: scores[d.key] ?? null })),
      tags: Array.from(selectedTags).map((key) => {
        const t = template.tags.find((x) => x.key === key)!;
        return { key, label: t.label };
      }),
    };
    try {
      const updated = await api.put<Evaluation>(`/evaluations/artifacts/${artifact.id}`, payload);
      setEvaluation(updated);
      onChanged();
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  return (
    <div className="candidate">
      <img src={`/api/artifacts/${artifact.id}/file`} alt={artifact.relative_path} />
      <div>
        <strong>{artifact.relative_path}</strong>
        <div className="muted">
          {translateTransferStatus(artifact.transfer_status)} · 校验 {artifact.checksum.slice(0, 8)}
        </div>
      </div>
      {artifact.extracted_metadata.length > 0 && (
        <details>
          <summary className="muted">提取的元数据</summary>
          <dl>
            {artifact.extracted_metadata.map((m) => (
              <div key={m.field_name}>
                <dt>{translateMetaField(m.field_name)}</dt>
                <dd>
                  {m.is_unknown ? (
                    <em className="muted">未知</em>
                  ) : (
                    <span>
                      {m.field_value}
                      {m.is_user_corrected && <span className="muted">（已修正）</span>}
                    </span>
                  )}
                </dd>
              </div>
            ))}
          </dl>
        </details>
      )}
      <div>
        <label>
          结果
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as Evaluation["status"])}
          >
            <option value="success">成功</option>
            <option value="partial_success">部分成功</option>
            <option value="failure">失败</option>
          </select>
        </label>
        <label>
          总分（1-10）
          <input
            type="number"
            min={1}
            max={10}
            value={overall}
            onChange={(e) => setOverall(e.target.value === "" ? "" : Number(e.target.value))}
          />
        </label>
        <label>
          <input
            type="checkbox"
            checked={isComplete}
            onChange={(e) => setIsComplete(e.target.checked)}
          />{" "}
          标记为已完成
        </label>
      </div>
      {template && (
        <div>
          <strong>维度</strong>
          <div className="grid">
            {template.dimensions
              .filter((d) => !d.is_disabled)
              .map((d) => (
                <label key={d.id}>
                  {d.label}
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={scores[d.key] ?? ""}
                    onChange={(e) =>
                      setScores({
                        ...scores,
                        [d.key]: e.target.value === "" ? "" : Number(e.target.value),
                      })
                    }
                  />
                </label>
              ))}
          </div>
        </div>
      )}
      {template && (
        <div>
          <strong>失败标签</strong>
          <div className="tag-list">
            {template.tags
              .filter((t) => !t.is_disabled)
              .map((t) => (
                <label key={t.id} className="tag" style={{ cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={selectedTags.has(t.key)}
                    onChange={(e) => {
                      const next = new Set(selectedTags);
                      if (e.target.checked) next.add(t.key);
                      else next.delete(t.key);
                      setSelectedTags(next);
                    }}
                  />{" "}
                  {t.label}
                </label>
              ))}
          </div>
        </div>
      )}
      <label>
        备注
        <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} />
      </label>
      {evaluation && (
        <div className="muted">
          来源：<code>{translateProvenance(evaluation.provenance)}</code> · 更新于{" "}
          {new Date(evaluation.updated_at).toLocaleString()}
        </div>
      )}
      <div className="actions">
        <button onClick={() => save("human")}>保存评分</button>
        {err && <span className="error">{err}</span>}
      </div>
    </div>
  );
}

function translateTransferStatus(s: string): string {
  switch (s) {
    case "transferred":
      return "已传输";
    case "failed":
      return "失败";
    case "pending":
      return "等待中";
    case "unstable":
      return "不稳定";
    default:
      return s;
  }
}

function translateMetaField(k: string): string {
  switch (k) {
    case "prompt":
      return "提示词";
    case "workflow":
      return "工作流";
    case "model":
      return "模型";
    case "seed":
      return "随机种子";
    case "steps":
      return "步数";
    case "sampler":
      return "采样器";
    case "cfg":
      return "CFG";
    default:
      return k;
  }
}

function translateProvenance(p: string): string {
  switch (p) {
    case "human":
      return "人工";
    case "ai_confirmed":
      return "AI 建议（已确认）";
    case "ai_edited":
      return "AI 建议（已编辑）";
    default:
      return p;
  }
}
