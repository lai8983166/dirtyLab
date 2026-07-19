import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { ExperimentDetail } from "../api/types";

export function NewExperimentPage() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [goal, setGoal] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!file) {
      setError("必须上传原图。");
      return;
    }
    const form = new FormData();
    form.append("name", name);
    form.append("goal", goal);
    form.append("original_image", file);
    setBusy(true);
    setError(null);
    try {
      const created = await api.post<ExperimentDetail>("/experiments", form);
      navigate(`/experiments/${created.id}`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page">
      <h1>新建实验</h1>
      <form
        className="grid"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <label className="span-2">
          名称
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label className="span-2">
          目标 / 描述
          <textarea value={goal} onChange={(e) => setGoal(e.target.value)} rows={3} />
        </label>
        <label className="span-2">
          原图
          <input
            type="file"
            accept="image/*"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            required
          />
        </label>
        <div className="span-2 actions">
          <button type="submit" disabled={busy || !file || !name}>
            {busy ? "创建中…" : "创建实验"}
          </button>
          {error && <span className="error">{error}</span>}
        </div>
      </form>
    </section>
  );
}
