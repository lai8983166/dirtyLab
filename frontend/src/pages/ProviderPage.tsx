import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Provider } from "../api/types";

export function ProviderPage() {
  const [provider, setProvider] = useState<Provider | null>(null);
  const [kind, setKind] = useState("openai_compatible");
  const [baseUrl, setBaseUrl] = useState("https://api.openai.com/v1");
  const [model, setModel] = useState("gpt-4o");
  const [apiKey, setApiKey] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get<Provider | null>("/providers").then((p) => {
      if (!p) return;
      setProvider(p);
      setKind(p.kind);
      setBaseUrl(p.base_url);
      setModel(p.model);
    });
  }, []);

  async function save() {
    setBusy(true);
    setErr(null);
    try {
      const updated = await api.put<Provider>("/providers", {
        kind,
        base_url: baseUrl,
        model,
        api_key: apiKey,
      });
      setProvider(updated);
      setApiKey("");
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page">
      <h1>AI 服务商</h1>
      <p className="muted">
        平台只保留一个 AI 服务商。API Key 保存在本地 <code>data/secrets/</code> 下，
        绝不会写入日志，绝不会同步出去，也绝不会出现在实验记录里。
      </p>
      <p className="muted">
        默认适配器说 OpenAI 兼容的 <code>/chat/completions</code> 协议，支持 OpenAI、
        Azure OpenAI、OpenRouter、Together、vLLM、Ollama、LM Studio。
      </p>
      <form className="grid" onSubmit={(e) => { e.preventDefault(); save(); }}>
        <label>
          类型
          <select value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="openai_compatible">openai_compatible（OpenAI 兼容）</option>
          </select>
        </label>
        <label>
          模型
          <input value={model} onChange={(e) => setModel(e.target.value)} required />
        </label>
        <label className="span-2">
          Base URL
          <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} required />
        </label>
        <label className="span-2">
          API Key
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={provider ? "••• 已保存；粘贴新 Key 替换 •••" : "sk-..."}
          />
        </label>
        <div className="span-2 actions">
          <button type="submit" disabled={busy || (!apiKey && !provider) || !baseUrl || !model}>
            {busy ? "保存中…" : provider ? "更新服务商" : "保存服务商"}
          </button>
          {err && <span className="error">{err}</span>}
        </div>
      </form>
      {provider && (
        <div className="card span-2">
          <h2>已保存的设置</h2>
          <dl>
            <dt>类型</dt>
            <dd>{provider.kind}</dd>
            <dt>模型</dt>
            <dd>{provider.model}</dd>
            <dt>API Key 位置</dt>
            <dd><code>data/secrets/{provider.api_key_ref}</code></dd>
          </dl>
        </div>
      )}
      <div className="card span-2">
        <h2>第三方数据披露</h2>
        <p className="muted">
          当你在候选图上点击 <em>请求 AI 分析</em> 时，平台会把选中的图片、实验目标、
          可用的工作流 + 元数据、以及（如果勾选）相关的已确认评分一起发送给配置的服务商。
          在你点那个按钮之前，<strong>不会有任何数据离开你的机器</strong>。
        </p>
      </div>
    </section>
  );
}
