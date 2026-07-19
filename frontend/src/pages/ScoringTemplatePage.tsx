import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Template } from "../api/types";

interface Draft {
  key: string;
  label: string;
}

export function ScoringTemplatePage() {
  const [template, setTemplate] = useState<Template | null>(null);
  const [history, setHistory] = useState<Template[]>([]);
  const [draftDims, setDraftDims] = useState<Draft[]>([]);
  const [draftTags, setDraftTags] = useState<Draft[]>([]);
  const [err, setErr] = useState<string | null>(null);

  const load = () => {
    api.get<Template>("/scoring").then(setTemplate).catch((e) => setErr(e.message));
    api.get<Template[]>("/scoring/all").then(setHistory).catch(() => setHistory([]));
  };

  useEffect(load, []);

  function addDim() {
    setDraftDims([...draftDims, { key: `dim_${Date.now()}`, label: "" }]);
  }
  function addTag() {
    setDraftTags([...draftTags, { key: `tag_${Date.now()}`, label: "" }]);
  }

  async function save() {
    const dimensions = draftDims.filter((d) => d.label.trim());
    const tags = draftTags.filter((t) => t.label.trim());
    if (dimensions.length === 0) {
      setErr("至少需要一个维度。");
      return;
    }
    try {
      await api.post<Template>("/scoring", {
        dimensions: dimensions.map((d, i) => ({ ...d, order: i, disabled: false })),
        tags: tags.map((t, i) => ({ ...t, order: i, disabled: false })),
      });
      setDraftDims([]);
      setDraftTags([]);
      load();
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  async function toggleDim(dimKey: string, dimId: string, disabled: boolean) {
    if (!template) return;
    try {
      const updated = template.dimensions.map((d) =>
        d.id === dimId ? { ...d, is_disabled: !disabled } : d,
      );
      await api.post<Template>("/scoring", {
        dimensions: updated.map((d, i) => ({
          key: d.key,
          label: d.label,
          order: i,
          disabled: d.is_disabled,
        })),
        tags: template.tags.map((t, i) => ({
          key: t.key,
          label: t.label,
          order: i,
          disabled: t.is_disabled,
        })),
      });
      load();
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  return (
    <section className="page">
      <h1>评分模板</h1>
      <p className="muted">
        新增、重命名、禁用、重排维度只影响<strong>后续</strong>评分。历史评分会保留原来的维度标签和分数。
      </p>
      {err && <p className="error">{err}</p>}

      {template && (
        <div className="card span-2">
          <h2>
            当前模板（版本 v{template.version}）
          </h2>
          <table>
            <thead>
              <tr>
                <th>顺序</th>
                <th>键</th>
                <th>名称</th>
                <th>是否禁用</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {template.dimensions.map((d, i) => (
                <tr key={d.id}>
                  <td>{i + 1}</td>
                  <td>
                    <code>{d.key}</code>
                  </td>
                  <td>{d.label}</td>
                  <td>{d.is_disabled ? "是" : "否"}</td>
                  <td>
                    <button
                      className="secondary"
                      onClick={() => toggleDim(d.key, d.id, d.is_disabled)}
                    >
                      {d.is_disabled ? "启用" : "禁用"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <h3>失败标签</h3>
          <div className="tag-list">
            {template.tags.map((t) => (
              <span key={t.id} className="tag">
                {t.label}
              </span>
            ))}
            {template.tags.length === 0 && <span className="muted">无</span>}
          </div>
        </div>
      )}

      <div className="card span-2">
        <h2>创建新版本</h2>
        <h3>维度</h3>
        {draftDims.map((d, i) => (
          <div key={i} className="grid" style={{ marginBottom: 6 }}>
            <input
              placeholder="键"
              value={d.key}
              onChange={(e) => {
                const next = [...draftDims];
                next[i] = { ...next[i], key: e.target.value };
                setDraftDims(next);
              }}
            />
            <input
              placeholder="名称"
              value={d.label}
              onChange={(e) => {
                const next = [...draftDims];
                next[i] = { ...next[i], label: e.target.value };
                setDraftDims(next);
              }}
            />
          </div>
        ))}
        <button className="secondary" onClick={addDim}>
          + 维度
        </button>

        <h3>失败标签</h3>
        {draftTags.map((t, i) => (
          <div key={i} className="grid" style={{ marginBottom: 6 }}>
            <input
              placeholder="键"
              value={t.key}
              onChange={(e) => {
                const next = [...draftTags];
                next[i] = { ...next[i], key: e.target.value };
                setDraftTags(next);
              }}
            />
            <input
              placeholder="名称"
              value={t.label}
              onChange={(e) => {
                const next = [...draftTags];
                next[i] = { ...next[i], label: e.target.value };
                setDraftTags(next);
              }}
            />
          </div>
        ))}
        <button className="secondary" onClick={addTag}>
          + 标签
        </button>

        <div style={{ marginTop: 12 }}>
          <button onClick={save}>保存为新版本</button>
        </div>
      </div>

      {history.length > 1 && (
        <div className="card span-2">
          <h2>历史版本</h2>
          <ul className="list">
            {history.map((t) => (
              <li key={t.id}>
                v{t.version} {t.is_active ? "（当前）" : ""}
                <span className="muted">
                  {" "}
                  · {t.dimensions.length} 个维度，{t.tags.length} 个标签
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
