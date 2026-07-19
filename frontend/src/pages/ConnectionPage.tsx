import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Connection, ConnectionTestResult } from "../api/types";

type SaveStage = "ssh_access" | "remote_root" | "comfyui_input" | "comfyui_output";

const STAGE_LABELS: Record<SaveStage, string> = {
  ssh_access: "SSH 连接",
  remote_root: "远端实验根目录",
  comfyui_input: "ComfyUI 输入目录",
  comfyui_output: "ComfyUI 输出目录",
};

export function ConnectionPage() {
  const [conn, setConn] = useState<Connection | null>(null);
  const [host, setHost] = useState("");
  const [port, setPort] = useState(22);
  const [username, setUsername] = useState("");
  const [privateKey, setPrivateKey] = useState("");
  const [remoteRoot, setRemoteRoot] = useState("");
  const [inputPath, setInputPath] = useState("input");
  const [outputPrefix, setOutputPrefix] = useState("ComfyUI_");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const [testing, setTesting] = useState(false);
  const [test, setTest] = useState<ConnectionTestResult | null>(null);

  useEffect(() => {
    api.get<Connection | null>("/connections").then((c) => {
      if (!c) return;
      setConn(c);
      setHost(c.host);
      setPort(c.port);
      setUsername(c.username);
      setRemoteRoot(c.remote_root);
      setInputPath(c.comfyui_input_path);
      setOutputPrefix(c.comfyui_output_prefix);
    });
  }, []);

  async function save() {
    setSaving(true);
    setSaveError(null);
    try {
      const updated = await api.put<Connection>("/connections", {
        host,
        port,
        username,
        private_key: privateKey,
        remote_root: remoteRoot,
        comfyui_input_path: inputPath,
        comfyui_output_prefix: outputPrefix,
      });
      setConn(updated);
      setPrivateKey(""); // 保存后清空，绝不在组件状态里保留
    } catch (e) {
      setSaveError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function runTest() {
    setTesting(true);
    setTest(null);
    try {
      const result = await api.post<ConnectionTestResult>("/connections/test");
      setTest(result);
    } catch (e) {
      setTest({
        ok: false,
        stage: "ssh_access",
        detail: (e as Error).message,
        resolved_paths: null,
      });
    } finally {
      setTesting(false);
    }
  }

  return (
    <section className="page">
      <h1>AutoDL 连接</h1>
      <p className="muted">
        平台只保留一个 AutoDL SSH 连接。私钥保存在本地{" "}
        <code>data/secrets/</code> 下，绝不会写入日志，也绝不会同步出去。
      </p>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          save();
        }}
        className="grid"
      >
        <label>
          主机
          <input value={host} onChange={(e) => setHost(e.target.value)} required />
        </label>
        <label>
          端口
          <input
            type="number"
            value={port}
            onChange={(e) => setPort(Number(e.target.value))}
            required
          />
        </label>
        <label>
          用户名
          <input value={username} onChange={(e) => setUsername(e.target.value)} required />
        </label>
        <label className="span-2">
          私钥（OpenSSH 格式）
          <textarea
            value={privateKey}
            onChange={(e) => setPrivateKey(e.target.value)}
            placeholder={
              conn ? "••• 已保存在本地；粘贴新私钥替换 •••" : "-----BEGIN OPENSSH PRIVATE KEY-----"
            }
            rows={6}
          />
        </label>
        <label className="span-2">
          远端实验根目录
          <input
            value={remoteRoot}
            onChange={(e) => setRemoteRoot(e.target.value)}
            placeholder="/root/ComfyUI"
            required
          />
        </label>
        <label>
          ComfyUI 输入目录（相对路径）
          <input value={inputPath} onChange={(e) => setInputPath(e.target.value)} />
        </label>
        <label>
          Save Image 文件名前缀
          <input value={outputPrefix} onChange={(e) => setOutputPrefix(e.target.value)} />
        </label>
        <div className="span-2 actions">
          <button type="submit" disabled={saving || !host || !username || !remoteRoot || (!privateKey && !conn)}>
            {saving ? "保存中…" : conn ? "更新连接" : "保存连接"}
          </button>
          {saveError && <span className="error">{saveError}</span>}
        </div>
      </form>

      <div className="card span-2">
        <h2>连接测试</h2>
        <p className="muted">
          测试会依次检查 SSH 连接、远端实验根目录、ComfyUI 工作目录。每个阶段独立报告。
        </p>
        <button onClick={runTest} disabled={testing || !conn}>
          {testing ? "测试中…" : "运行测试"}
        </button>
        {test && (
          <div className={`test-result ${test.ok ? "ok" : "fail"}`}>
            <h3>
              {test.ok
                ? "连接成功"
                : `失败阶段：${STAGE_LABELS[test.stage as SaveStage] ?? test.stage}`}
            </h3>
            {test.detail && <p>{test.detail}</p>}
            {test.resolved_paths && (
              <ul>
                {Object.entries(test.resolved_paths).map(([k, v]) => (
                  <li key={k}>
                    <strong>{translatePathKey(k)}</strong>：<code>{v}</code>
                  </li>
                ))}
              </ul>
            )}
            {test.stage === "ssh_access" && !test.ok && (
              <p className="muted">
                常见原因：AutoDL 实例未启动、SSH 密钥不匹配、用户名错误，或者端口被防火墙拦截。
              </p>
            )}
            {test.stage === "remote_root" && !test.ok && (
              <p className="muted">
                修改上面的"远端实验根目录"，让它指向包含 <code>input/</code> 和{" "}
                <code>output/</code> 的目录。
              </p>
            )}
          </div>
        )}
      </div>

      {conn && (
        <div className="card span-2">
          <h2>已保存的设置</h2>
          <dl>
            <dt>最近测试结果</dt>
            <dd>{translateTestStatus(conn.last_test_status)}</dd>
            <dt>最近测试时间</dt>
            <dd>{conn.last_test_at ? new Date(conn.last_test_at).toLocaleString() : "—"}</dd>
            <dt>私钥位置</dt>
            <dd>
              <code>data/secrets/{conn.private_key_ref}</code>
            </dd>
          </dl>
        </div>
      )}
    </section>
  );
}

function translatePathKey(k: string): string {
  switch (k) {
    case "remote_root":
      return "远端根目录";
    case "comfyui_input":
      return "ComfyUI 输入";
    case "comfyui_output":
      return "ComfyUI 输出";
    default:
      return k;
  }
}

function translateTestStatus(s: string | null): string {
  switch (s) {
    case "ok":
      return "成功";
    case "failed":
      return "失败";
    default:
      return "—";
  }
}
