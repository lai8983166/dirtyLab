import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import type { ExperimentDetail, SyncResult } from "../api/types";
import { CandidateComparison } from "../components/CandidateComparison";
import { AnalysisPanel } from "../components/AnalysisPanel";

export function ExperimentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<ExperimentDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null);

  const load = useCallback(() => {
    if (!id) return;
    api
      .get<ExperimentDetail>(`/experiments/${id}`)
      .then(setDetail)
      .catch((e) => setErr(e.message));
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  async function sync() {
    if (!id) return;
    setSyncing(true);
    setErr(null);
    setSyncResult(null);
    try {
      const result = await api.post<SyncResult>(`/sync/experiments/${id}`);
      setSyncResult(result);
      load();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setSyncing(false);
    }
  }

  if (!detail) {
    return <section className="page">{err ? <p className="error">{err}</p> : <p>加载中…</p>}</section>;
  }

  const candidates = detail.snapshots
    .flatMap((s) => s.artifacts)
    .filter((a) => a.kind === "saved_image");

  return (
    <section className="page">
      <h1>{detail.name}</h1>
      <p className="muted">
        创建于 {new Date(detail.created_at).toLocaleString()} · 状态 {translateStatus(detail.status)}
      </p>
      {detail.goal && <p>{detail.goal}</p>}

      <div className="card span-2">
        <h2>远端工作目录</h2>
        <p>
          把原图拷贝或软链到 ComfyUI 的 <code>input/</code> 目录，对每个需要保留的输出使用{" "}
          <code>Save Image</code> 节点。平台会同步以下类型的产物：
        </p>
        <ul>
          <li>
            原图：<code>{detail.remote_workspace_path}/input/</code>
          </li>
          <li>
            保存的图：<code>{detail.remote_workspace_path}/output/</code>
          </li>
          <li>
            遮罩：<code>{detail.remote_workspace_path}/masks/</code>
          </li>
          <li>
            工作流 JSON（导出在输出旁边，例如 <code>*.json</code>）
          </li>
        </ul>
        <p>
          <strong>你的远端工作目录：</strong>
          <br />
          <code>{detail.remote_workspace_path}</code>
        </p>
      </div>

      <div className="card span-2">
        <h2>原图</h2>
        <img
          src={`/api/experiments/${detail.id}/original-image`}
          alt="原图"
          style={{ maxWidth: 400 }}
        />
      </div>

      <div className="card span-2">
        <h2>同步</h2>
        <p className="muted">
          只支持手动同步。平台不会轮询 AutoDL，同步时也绝不会调用 AI。
        </p>
        <button onClick={sync} disabled={syncing}>
          {syncing ? "同步中…" : "立即同步"}
        </button>
        {syncResult && (
          <div className={`test-result ${syncResult.snapshot.status === "success" ? "ok" : "fail"}`}>
            <h3>
              快照 #{syncResult.snapshot.number} · {translateSnapshotStatus(syncResult.snapshot.status)}
            </h3>
            <p>
              传输 {syncResult.snapshot.artifacts.length} 个文件，忽略 {syncResult.ignored_count} 个。
            </p>
            {syncResult.partial_failures.length > 0 && (
              <ul>
                {syncResult.partial_failures.map((f, i) => (
                  <li key={i}>
                    <code>{f.path}</code>：{f.reason}
                  </li>
                ))}
              </ul>
            )}
            {syncResult.retryable && (
              <button className="secondary" onClick={sync}>
                重试
              </button>
            )}
          </div>
        )}
      </div>

      <div className="card span-2">
        <h2>候选图（{candidates.length}）</h2>
        {candidates.length === 0 ? (
          <p className="muted">还没有候选图。同步一个快照后这里会显示。</p>
        ) : (
          <CandidateComparison artifacts={candidates} onChange={load} />
        )}
      </div>

      <div className="card span-2">
        <h2>AI 分析历史</h2>
        <AnalysisPanel
          experimentId={detail.id}
          candidates={candidates}
          analyses={detail.analyses}
          onChanged={load}
        />
      </div>

      {err && <p className="error">{err}</p>}
    </section>
  );
}

function translateStatus(s: string): string {
  switch (s) {
    case "created":
      return "已创建";
    case "synced":
      return "已同步";
    default:
      return s;
  }
}

function translateSnapshotStatus(s: string): string {
  switch (s) {
    case "success":
      return "成功";
    case "partial":
      return "部分成功";
    case "failed":
      return "失败";
    case "empty":
      return "空";
    default:
      return s;
  }
}
