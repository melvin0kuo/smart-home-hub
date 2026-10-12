import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Radio } from "lucide-react";
import { api } from "../services/api";

export function InfraredPanel({ readOnly }: { readOnly: boolean }) {
  const remotes = useQuery({
    queryKey: ["infrared"],
    queryFn: api.infrared,
    retry: 1,
  });
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  async function send(id: string, command: string) {
    setBusy(true);
    try {
      const result = await api.infraredCommand(id, command);
      setMessage(result.message);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "指令傳送失敗");
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="devices-section">
      <div className="section-heading">
        <div>
          <h2>紅外線遙控器</h2>
          <p>僅已驗證指令可以操作；紅外線送出不代表電器已完成動作。</p>
        </div>
      </div>
      {message && <p role="status">{message}</p>}
      {remotes.isPending && <p>正在讀取遙控器…</p>}
      {remotes.isError && (
        <p role="alert">
          無法讀取遙控器。
          <button onClick={() => void remotes.refetch()}>重試</button>
        </p>
      )}
      {remotes.data?.length === 0 && (
        <p>尚未設定紅外線設備。請先在 HA 驗證可用的控制介面。</p>
      )}
      <div className="device-grid">
        {remotes.data?.map((remote) => (
          <article className="device-card" key={remote.id}>
            <Radio size={28} />
            <h3>{remote.name}</h3>
            <p>{remote.gateway}</p>
            <details className="remote-note">
              <summary>整合資訊與限制</summary>
              <p>{remote.note}</p>
            </details>
            {remote.supported ? (
              <div className="camera-actions">
                {remote.commands.map((cmd) => (
                  <button
                    key={cmd.id}
                    disabled={readOnly || busy}
                    onClick={() => void send(remote.id, cmd.id)}
                  >
                    {cmd.label}
                  </button>
                ))}
              </div>
            ) : (
              <p>待支援 · 尚未取得可用控制指令</p>
            )}
          </article>
        ))}
      </div>
      <p className="muted">
        按鍵來自 H110 已儲存的遙控設定；電器是否收到指令仍需現場確認。
        冷氣與未確認用途的按鍵會保留待驗證。
      </p>
    </section>
  );
}
