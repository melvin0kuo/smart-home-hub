import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  ArrowUpRight,
  Camera,
  Check,
  ChevronRight,
  CircleHelp,
  Cpu,
  House,
  LayoutGrid,
  LogOut,
  Moon,
  MoreHorizontal,
  Plug,
  Radio,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Sun,
  Thermometer,
  Wifi,
  WifiOff,
  Zap,
} from "lucide-react";
import { homeEnvironment } from "../services/environment";
import { api, ApiError } from "../services/api";
import type { Action, Session } from "../types/device";
import { DeviceShortcut } from "../components/DeviceShortcut";
import { DeviceDetails } from "../components/DeviceDetails";
import { DeviceCard } from "../components/DeviceCard";
import { InfraredPanel } from "../components/InfraredPanel";
type View = "overview" | "devices" | "power" | "camera" | "infrared" | "setup";
export function Dashboard({
  session,
  onLogout,
}: {
  session: Session;
  onLogout: () => void;
}) {
  const queryClient = useQueryClient();
  const devices = useQuery({
      queryKey: ["devices"],
      queryFn: api.devices,
      retry: 1,
    }),
    history = useQuery({
      queryKey: ["history"],
      queryFn: api.history,
      retry: 1,
    }),
    scenes = useQuery({ queryKey: ["scenes"], queryFn: api.scenes, retry: 1 });
  const [detailId, setDetailId] = useState<string | null>(null);
  const [view, setView] = useState<View>("overview"),
    [room, setRoom] = useState("全部空間"),
    [search, setSearch] = useState(""),
    [notice, setNotice] = useState(""),
    [error, setError] = useState(""),
    [connected, setConnected] = useState(false),
    [sceneBusy, setSceneBusy] = useState(false),
    [moreOpen, setMoreOpen] = useState(false);
  function navigate(next: View) {
    setView(next);
    setRoom("全部空間");
    setSearch("");
    setMoreOpen(false);
    window.scrollTo({ top: 0, behavior: "instant" });
  }
  const [dark, setDark] = useState(
    () => localStorage.getItem("hub-theme") === "dark",
  );
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    localStorage.setItem("hub-theme", dark ? "dark" : "light");
  }, [dark]);
  useEffect(() => {
    let disposed = false,
      socket: WebSocket | undefined,
      timer: number | undefined,
      attempt = 0;
    const refresh = () => {
      void queryClient.invalidateQueries({ queryKey: ["devices"] });
      void queryClient.invalidateQueries({ queryKey: ["history"] });
    };
    const connect = () => {
      if (disposed) return;
      socket = new WebSocket(
        `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/events`,
      );
      socket.onopen = () => {
        setConnected(true);
        attempt = 0;
        refresh();
      };
      socket.onmessage = () => refresh();
      socket.onerror = () => socket?.close();
      socket.onclose = () => {
        setConnected(false);
        if (!disposed)
          timer = window.setTimeout(
            connect,
            Math.min(1000 * 2 ** attempt++, 15000) + Math.random() * 300,
          );
      };
    };
    connect();
    return () => {
      disposed = true;
      window.clearTimeout(timer);
      socket?.close();
    };
  }, [queryClient]);
  useEffect(() => {
    if (devices.error instanceof ApiError && devices.error.status === 401)
      onLogout();
  }, [devices.error, onLogout]);
  const all = devices.data ?? [],
    online = all.filter((d) => d.online === true).length,
    sensor = homeEnvironment(all),
    power = all.find((d) => d.type === "power_strip");
  const shown = all.filter(
    (d) =>
      (room === "全部空間" || d.room === room) &&
      `${d.name} ${d.model} ${d.manufacturer}`
        .toLowerCase()
        .includes(search.toLowerCase()) &&
      (view !== "power" || d.type === "power_strip") &&
      (view !== "camera" || d.type === "camera"),
  );
  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ["devices"] });
    await queryClient.invalidateQueries({ queryKey: ["history"] });
  };
  async function act(id: string, action: Action) {
    setError("");
    try {
      await api.action(id, action);
      setNotice(
        session.mode === "mock" ? "模擬操作已確認" : "已收到設備目標狀態",
      );
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "操作失敗");
    }
  }
  async function scene(id: string, name: string) {
    setSceneBusy(true);
    setError("");
    try {
      const result = await api.scene(id);
      if (result.status !== "confirmed")
        throw new Error("部分情境操作失敗，請查看紀錄。");
      setNotice(`${name}已執行${session.mode === "mock" ? "（模擬）" : ""}`);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "情境失敗");
    } finally {
      setSceneBusy(false);
    }
  }
  async function logout() {
    try {
      await api.logout();
      queryClient.clear();
      onLogout();
    } catch (e) {
      setError(e instanceof Error ? e.message : "登出失敗");
    }
  }
  const navigation: [View, string, typeof House][] = [
    ["overview", "家庭總覽", House],
    ["devices", "裝置管理", LayoutGrid],
    ["camera", "攝影機", Camera],
    ["infrared", "紅外線遙控", Radio],
    ["power", "插座與用電", Zap],
    ["setup", "整合狀態", SlidersHorizontal],
  ];
  return (
    <div className={`app-shell view-${view}`}>
      <aside className="sidebar">
        <a
          className="brand"
          href="/"
          onClick={(e) => {
            e.preventDefault();
            navigate("overview");
          }}
        >
          <span>
            <House size={23} />
          </span>
          <div>
            Smart Home<small>HUB / 智慧家庭</small>
          </div>
        </a>
        <div className="home-selector">
          <div className="home-avatar">
            <House size={17} />
          </div>
          <div>
            <strong>我的家</strong>
            <small>私人家庭空間</small>
          </div>
          <ChevronRight size={15} />
        </div>
        <p className="nav-label">你的生活空間</p>
        <nav aria-label="主要導覽">
          {navigation.map(([id, label, Icon]) => (
            <button
              key={id}
              onClick={() => navigate(id)}
              aria-current={view === id ? "page" : undefined}
              title={label}
              className={view === id ? "selected" : ""}
            >
              <Icon size={19} />
              <span className="nav-text">{label}</span>
              {view === id && <span className="nav-dot" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="local-card">
            <ShieldCheck size={20} />
            <strong>為你的家，保留隱私</strong>
            <p>
              設備透過後端整合，
              <br />
              敏感資訊留在本機。
            </p>
          </div>
          <a href="/docs" target="_blank" rel="noreferrer">
            <CircleHelp size={17} /> API 文件
            <ArrowUpRight size={14} />
          </a>
          <div className="profile">
            <span>H</span>
            <div>
              <strong>
                {session.role === "admin" ? "家庭管理員" : "唯讀使用者"}
              </strong>
              <small>本機測試版本</small>
            </div>
            <button
              aria-label="登出"
              title="登出"
              onClick={() => void logout()}
            >
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </aside>
      <main className="main-content">
        <header className="topbar">
          <div>
            <span className="breadcrumb">我的家</span>
            <ChevronRight size={13} />
            <strong>{navigation.find((n) => n[0] === view)?.[1]}</strong>
          </div>
          <div>
            <span className={`event-status ${connected ? "" : "disconnected"}`}>
              {connected ? <Wifi size={14} /> : <WifiOff size={14} />}
              <span>{connected ? "平台即時連線" : "連線恢復中"}</span>
            </span>
            <button
              className="icon-button mobile-logout"
              aria-label="登出"
              onClick={() => void logout()}
            >
              <LogOut size={18} />
            </button>
            <button
              className="icon-button"
              aria-label="切換色彩模式"
              onClick={() => setDark(!dark)}
            >
              {dark ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>
        </header>
        <section className="page">
          <div className="page-heading">
            <div>
              <p className="eyebrow">HOME, CONNECTED.</p>
              <h1>
                {view === "overview"
                  ? "我的家庭"
                  : navigation.find((n) => n[0] === view)?.[1]}
              </h1>
              <p>
                {
                  {
                    overview: "常用控制、設備狀態與最近動態。",
                    devices: "依房間尋找設備，操作已開放的功能。",
                    camera: "先確認隱私狀態，再觀看影像或調整方向。",
                    infrared: "選擇遙控器，操作家中的紅外線電器。",
                    power: "查看各插孔狀態與設備提供的用電資訊。",
                    setup: "查看目前整合能力與後續準備事項。",
                  }[view]
                }
              </p>
            </div>
            <span className="date-label">
              {new Intl.DateTimeFormat("zh-TW", {
                month: "long",
                day: "numeric",
                weekday: "long",
                timeZone: "Asia/Taipei",
              }).format(new Date())}
            </span>
          </div>
          {(session.mode === "mock" ||
            view === "overview" ||
            view === "setup") && (
            <div
              className={`mode-banner ${session.mode === "real" ? "real" : ""}`}
            >
              <Cpu size={18} />
              <strong>
                {session.mode === "mock"
                  ? "Mock Mode · 模擬測試環境"
                  : "Real Mode · 真實整合環境"}
              </strong>
              <span>
                {session.mode === "mock"
                  ? "所有數值與操作均為模擬，尚未控制真實設備。"
                  : "僅對已驗證的設備能力開放操作。"}
              </span>
              <span className="version">v0.1</span>
            </div>
          )}
          {error && (
            <div className="feedback error" role="alert">
              {error}
              <button onClick={() => setError("")}>關閉</button>
            </div>
          )}
          {notice && (
            <div className="feedback success" role="status">
              <Check size={17} />
              {notice}
              <button onClick={() => setNotice("")}>關閉</button>
            </div>
          )}
          {devices.isError && (
            <div className="feedback error" role="alert">
              {devices.error.message}
              <button onClick={() => void devices.refetch()}>重新連線</button>
            </div>
          )}
          {view === "infrared" ? (
            <InfraredPanel readOnly={session.role === "viewer"} />
          ) : view === "setup" ? (
            <section className="setup-panel">
              <Radio size={34} />
              <h2>設備整合與後續準備</h2>
              <p>
                先準備 Home
                Assistant，再逐台驗證設備。此平台不會自動修改配對或韌體。
              </p>
              <ol>
                <li>確認常駐 Home Assistant 主機、內網位址與版本。</li>
                <li>記錄設備標籤、硬體與韌體版本。</li>
                <li>依設定指南完成授權與配對，逐項確認設備能力。</li>
                <li>尚未完成整合的設備，請查看下方限制與所需條件。</li>
                <li>移植樹莓派時，依專案啟動指南重建環境。</li>
              </ol>
              <p>
                攝影機與紅外線遙控依已驗證能力開放；香氛機仍需相容網關與實機驗證。
              </p>
              <div className="integration-list">
                {all.map((d) => (
                  <div key={d.id}>
                    <strong>{d.name}</strong>
                    <span>{d.available ? "可用" : "待處理"}</span>
                    <p>
                      {d.integration_note ??
                        d.attributes.note ??
                        "詳細能力請查看裝置卡片。"}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          ) : (
            <>
              {view === "overview" && (
                <div className="summary-grid">
                  <div className="summary-card">
                    <span className="summary-icon mint">
                      <LayoutGrid size={20} />
                    </span>
                    <div>
                      <p>已登錄設備</p>
                      <strong>
                        {all.length}
                        <small>台</small>
                      </strong>
                    </div>
                    <span className="summary-caption">
                      Tapo{" "}
                      {all.filter((d) => d.manufacturer === "TP-Link").length} ·
                      Xiaomi{" "}
                      {all.filter((d) => d.manufacturer === "Xiaomi").length}
                    </span>
                  </div>
                  <div className="summary-card">
                    <span className="summary-icon blue">
                      <Wifi size={20} />
                    </span>
                    <div>
                      <p>在線設備</p>
                      <strong>
                        {online}
                        <small>/ {all.length}</small>
                      </strong>
                    </div>
                    <span className="summary-caption">
                      {all.filter((d) => d.online === false).length} 離線 ·{" "}
                      {all.filter((d) => d.online === null).length} 待確認
                    </span>
                  </div>
                  {(sensor || all.some((d) => d.type === "dehumidifier")) && (
                    <div className="summary-card">
                      <span className="summary-icon peach">
                        <Thermometer size={20} />
                      </span>
                      <div>
                        <p>家庭溫濕度</p>
                        <strong>
                          {sensor?.attributes.temperature ?? "—"}
                          <small>°C</small>
                        </strong>
                      </div>
                      <span className="summary-caption">
                        {sensor
                          ? `相對濕度 ${sensor.attributes.humidity ?? "—"}% · 來源：${sensor.name}`
                          : "暫無資料 · 除濕機未連線"}
                      </span>
                    </div>
                  )}
                  {power?.attributes.power_w !== undefined && (
                    <div className="summary-card">
                      <span className="summary-icon yellow">
                        <Zap size={20} />
                      </span>
                      <div>
                        <p>目前功率</p>
                        <strong>
                          {power?.attributes.power_w ?? "—"}
                          <small>W</small>
                        </strong>
                      </div>
                      <span className="summary-caption">
                        {power?.attributes.power_w !== undefined
                          ? "設備回報功率"
                          : "設備尚未提供功率資料"}
                      </span>
                    </div>
                  )}
                </div>
              )}
              {view === "overview" &&
                all.some((d) => !d.available || d.stale) && (
                  <div className="attention-banner" role="status">
                    <WifiOff size={20} />
                    <div>
                      <strong>
                        {all.filter((d) => !d.available || d.stale).length}{" "}
                        台設備需要留意
                      </strong>
                      <p>離線、資料過期或尚未完成整合的設備，暫時無法操作。</p>
                    </div>
                    <button onClick={() => navigate("devices")}>
                      查看裝置
                    </button>
                  </div>
                )}
              {view === "overview" && (scenes.data?.length ?? 0) > 0 && (
                <section className="scenes">
                  <div className="section-heading">
                    <h2>常用情境</h2>
                    <span>快速情境</span>
                  </div>
                  <div className="scene-grid">
                    {scenes.data?.map((s, index) => {
                      const Icon =
                        [House, ArrowUpRight, Moon, Sun][index] ?? House;
                      return (
                        <button
                          key={s.id}
                          disabled={sceneBusy || session.role === "viewer"}
                          onClick={() => void scene(s.id, s.name)}
                        >
                          <span className={`scene-icon scene-${index}`}>
                            <Icon size={21} />
                          </span>
                          <div>
                            <strong>{s.name}</strong>
                            <small>點一下，切換生活節奏</small>
                          </div>
                          <ChevronRight size={16} />
                        </button>
                      );
                    })}
                    {scenes.data?.length === 0 && (
                      <p className="muted">尚未設定已驗證的情境。</p>
                    )}
                  </div>
                </section>
              )}
              <section className="devices-section">
                <div className="section-heading">
                  <div>
                    <h2>
                      {view === "camera"
                        ? "攝影機"
                        : view === "power"
                          ? "插座與用電"
                          : "我的設備"}{" "}
                      <span className="count">{shown.length}</span>
                    </h2>
                    <p>
                      {view === "power"
                        ? `${session.mode === "mock" ? "P306 尚未確認提供用電資訊" : "僅顯示已映射設備回報的功率"}，歷史用電與電價統計尚未啟用。`
                        : view === "camera"
                          ? "登入後播放私人即時影像；旋轉控制依設備驗證結果開放。"
                          : "依設備已驗證能力，呈現適合的控制方式。"}
                    </p>
                  </div>
                  {(view === "devices" || view === "overview") && (
                    <label className="search-box">
                      <Search size={16} />
                      <input
                        aria-label="搜尋設備"
                        placeholder="搜尋設備或型號"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                      />
                    </label>
                  )}
                </div>
                {(view === "devices" || view === "overview") && (
                  <div className="room-tabs" aria-label="房間篩選">
                    {["全部空間", ...new Set(all.map((d) => d.room))].map(
                      (r) => (
                        <button
                          aria-pressed={room === r}
                          className={room === r ? "active" : ""}
                          key={r}
                          onClick={() => setRoom(r)}
                        >
                          {r}
                        </button>
                      ),
                    )}
                  </div>
                )}
                {devices.isPending ? (
                  <div className="empty-state">正在讀取設備…</div>
                ) : (
                  <div
                    className={
                      view === "camera" ? "device-grid" : "shortcut-grid"
                    }
                  >
                    {shown.map((d) =>
                      view !== "camera" ? (
                        <DeviceShortcut
                          key={d.id}
                          device={d}
                          onAction={act}
                          readOnly={session.role === "viewer"}
                          onOpen={() => {
                            setError("");
                            setNotice("");
                            setDetailId(d.id);
                          }}
                        />
                      ) : (
                        <DeviceCard
                          key={d.id}
                          device={d}
                          onAction={act}
                          readOnly={session.role === "viewer"}
                          compactCamera={view !== "camera"}
                          onOpenCamera={() => navigate("camera")}
                        />
                      ),
                    )}
                  </div>
                )}
                {!devices.isPending && shown.length === 0 && (
                  <div className="empty-state">沒有符合條件的設備。</div>
                )}
              </section>
              {view === "overview" && (
                <section className="activity-panel">
                  <div className="section-heading">
                    <h2>
                      <Activity size={19} /> 最近操作
                    </h2>
                    <span>以伺服器結果為準</span>
                  </div>
                  {history.isError ? (
                    <p className="error">無法取得紀錄，請重試。</p>
                  ) : history.data?.length ? (
                    <div className="activity-list">
                      {history.data.slice(0, 6).map((item) => (
                        <div key={item.operation_id}>
                          <span className="activity-icon">
                            <Plug size={16} />
                          </span>
                          <div>
                            <strong>
                              {all.find((d) => d.id === item.device_id)?.name ??
                                item.device_id}
                            </strong>
                            <span>
                              {item.target === "main"
                                ? ""
                                : item.target + " · "}
                              {(
                                {
                                  set_target_humidity: "調整目標濕度",
                                  set_mode: "切換模式",
                                  set_fan_speed: "調整風速",
                                  set_operative_mode: "切換運轉方式",
                                  turn_on: "開啟",
                                  turn_off: "關閉",
                                  set_brightness: "調整亮度",
                                  set_diffusion_duration: "調整出香時長",
                                  set_diffusion_interval: "調整出香間隔",
                                  set_color: "調整燈光顏色",
                                  set_color_temperature: "調整色溫",
                                  enable_privacy: "開啟隱私模式",
                                  disable_privacy: "關閉隱私模式",
                                } as Record<string, string>
                              )[item.action] ?? item.action}{" "}
                              · {item.mode === "mock" ? "模擬操作" : "設備操作"}
                            </span>
                          </div>
                          <span
                            className={`result ${item.status === "confirmed" ? "confirmed" : ""}`}
                          >
                            {item.status === "confirmed"
                              ? "已確認"
                              : item.status === "sent"
                                ? "已送出"
                                : item.status === "timeout"
                                  ? "待確認／逾時"
                                  : "失敗"}
                          </span>
                          <time>
                            {new Date(item.occurred_at).toLocaleTimeString(
                              "zh-TW",
                              { hour: "2-digit", minute: "2-digit" },
                            )}
                          </time>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="empty-activity">
                      <Activity size={22} />
                      <p>
                        {session.mode === "mock"
                          ? "還沒有操作紀錄。試著開啟一個模擬插孔。"
                          : "尚無平台操作紀錄；僅已驗證且開放的插孔可以控制。"}
                      </p>
                    </div>
                  )}
                </section>
              )}
            </>
          )}
          <footer className="page-footer">
            <span>
              <House size={14} /> Smart Home Hub
            </span>
            <span>
              本機優先，為日常而設計。
              {session.mode === "mock" ? " · 模擬模式" : ""}
            </span>
          </footer>
        </section>
      </main>
      {detailId && all.find((d) => d.id === detailId) && (
        <DeviceDetails
          device={all.find((d) => d.id === detailId)!}
          readOnly={session.role === "viewer"}
          onAction={act}
          error={error}
          notice={notice}
          onClose={() => setDetailId(null)}
          onInfrared={() => {
            setDetailId(null);
            navigate("infrared");
          }}
        />
      )}
      <nav className="mobile-nav" aria-label="手機導覽">
        {navigation.slice(0, 4).map(([id, label, Icon]) => (
          <button
            key={id}
            aria-current={view === id ? "page" : undefined}
            className={view === id ? "selected" : ""}
            onClick={() => navigate(id)}
          >
            <Icon size={21} />
            <span>
              {id === "overview"
                ? "總覽"
                : id === "devices"
                  ? "裝置"
                  : id === "infrared"
                    ? "遙控"
                    : label}
            </span>
          </button>
        ))}
        <button
          aria-expanded={moreOpen}
          aria-controls="mobile-more"
          className={view === "power" || view === "setup" ? "selected" : ""}
          onClick={() => setMoreOpen(!moreOpen)}
        >
          <MoreHorizontal size={21} />
          <span>更多</span>
        </button>
      </nav>
      {moreOpen && (
        <div className="mobile-more" id="mobile-more">
          <strong>更多功能</strong>
          {navigation.slice(4).map(([id, label, Icon]) => (
            <button key={id} onClick={() => navigate(id)}>
              <Icon size={20} />
              {label}
              <ChevronRight size={18} />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
