import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Experiment } from "../api/types";

export function ExperimentsPage() {
  const [items, setItems] = useState<Experiment[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.get<Experiment[]>("/experiments").then(setItems).catch((e) => setErr(e.message));
  }, []);

  return (
    <section className="page">
      <h1>实验列表</h1>
      <p className="muted">
        <Link to="/new">新建一个实验</Link>开始。
      </p>
      {err && <p className="error">{err}</p>}
      <ul className="list">
        {items.map((e) => (
          <li key={e.id}>
            <Link to={`/experiments/${e.id}`}>
              <strong>{e.name}</strong>
            </Link>
            <span className="muted"> · 状态：{translateStatus(e.status)}</span>
            <div className="muted">{e.goal || <em>未设置目标</em>}</div>
          </li>
        ))}
        {items.length === 0 && !err && <li className="muted">还没有实验。</li>}
      </ul>
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
