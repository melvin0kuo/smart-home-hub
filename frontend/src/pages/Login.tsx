import { useState, type FormEvent } from "react";
import { House, ArrowRight, ShieldCheck } from "lucide-react";
import { api } from "../services/api";
import type { Session } from "../types/device";
export function Login({ onLogin }: { onLogin: (s: Session) => void }) {
  const [username, setUsername] = useState("admin"),
    [password, setPassword] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      onLogin(await api.login(username, password));
      setPassword("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "登入失敗");
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="login-page">
      <div className="login-art">
        <div className="brand">
          <span>
            <House size={25} />
          </span>
          Smart Home Hub
        </div>
        <p className="eyebrow">A LITTLE CLOSER TO HOME</p>
        <h1>
          讓生活的節奏，
          <br />
          回到你的手中。
        </h1>
        <p>
          所有設備，一個熟悉的地方。
          <br />
          從這台電腦開始，打造屬於你的智慧家庭。
        </p>
        <div className="house-orbit">
          <House size={110} strokeWidth={0.8} />
          <span className="orbit o1" />
          <span className="orbit o2" />
          <span className="orbit o3" />
        </div>
        <div className="art-footer">
          <ShieldCheck size={17} /> 本機優先 · 安全存取 · 跨品牌整合
        </div>
      </div>
      <section className="login-form">
        <div>
          <p className="eyebrow">WELCOME HOME</p>
          <h2>歡迎回家</h2>
          <p>登入你的智慧家庭管理平台。</p>
          <form onSubmit={submit}>
            <label>
              帳號
              <input
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </label>
            <label>
              密碼
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>
            {error && (
              <p role="alert" className="error">
                {error}
              </p>
            )}
            <button className="primary" disabled={busy}>
              {busy ? "登入中…" : "登入平台"}
              <ArrowRight size={18} />
            </button>
          </form>
          <p className="login-hint">
            首次測試請使用 <code>admin</code>。隨機產生的本機密碼位於專案根目錄{" "}
            <code>.env</code> 的 <code>HUB_ADMIN_PASSWORD</code>。
          </p>
          <div className="local-label">
            <span className="green-dot" /> 本機測試環境 · 不預設開放網際網路
          </div>
        </div>
      </section>
    </main>
  );
}
