import { useEffect, useRef, useState } from "react";
import { ArrowLeft, Check, Plus, RefreshCw, ShieldCheck } from "lucide-react";
import { api } from "../services/api";
import {
  canEnableImportedControl,
  filterCandidates,
  type ImportFilter,
} from "../services/importSelection";
import type {
  ImportCandidate,
  ImportDiscovery,
  ImportItem,
} from "../types/imports";
import "../imports.css";

export function ImportCandidateList({
  candidates,
  selected,
  onToggle,
}: {
  candidates: ImportCandidate[];
  selected: string[];
  onToggle: (candidate: ImportCandidate) => void;
}) {
  return (
    <div className="import-candidates">
      {candidates.map((c) => (
        <label className="import-candidate" key={c.entity_id}>
          <input
            type="checkbox"
            checked={selected.includes(c.entity_id)}
            disabled={!c.supported || c.already_imported}
            onChange={() => onToggle(c)}
          />
          <span>
            <strong>{c.name}</strong>
            <code>{c.entity_id}</code>
            <small>
              {c.already_imported
                ? "已加入"
                : !c.supported
                  ? "待支援"
                  : !c.available
                    ? "離線 · 僅能唯讀匯入"
                    : "可加入"}
            </small>
            <p>{c.note}</p>
          </span>
        </label>
      ))}
    </div>
  );
}

type Selected = ImportItem & { safe: boolean };
export function DeviceImportWizard({
  onClose,
  onImported,
}: {
  onClose: () => void;
  onImported: () => Promise<void>;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [data, setData] = useState<ImportDiscovery | null>(null);
  const [selected, setSelected] = useState<Selected[]>([]);
  const [step, setStep] = useState(1);
  const [filter, setFilter] = useState<ImportFilter>("available");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [done, setDone] = useState(false);
  useEffect(() => {
    const element = dialog.current!;
    const focus = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    element.showModal();
    let active = true;
    api
      .importCandidates()
      .then((result) => {
        if (active) setData(result);
      })
      .catch((e) => {
        if (active)
          setError(e instanceof Error ? e.message : "無法取得候選設備");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
      element.close();
      document.body.style.overflow = overflow;
      focus?.focus({ preventScroll: true });
    };
  }, []);
  async function reload() {
    setLoading(true);
    setError("");
    try {
      const result = await api.importCandidates();
      setData(result);
      setSelected((items) =>
        items.filter((item) =>
          result.candidates.some(
            (c) =>
              c.entity_id === item.entity_id &&
              c.supported &&
              !c.already_imported,
          ),
        ),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "讀取失敗");
    } finally {
      setLoading(false);
    }
  }
  function update(entity: string, patch: Partial<Selected>) {
    setSelected((items) =>
      items.map((item) =>
        item.entity_id === entity ? { ...item, ...patch } : item,
      ),
    );
  }
  async function test(
    candidate: ImportCandidate,
    action: "turn_on" | "turn_off",
  ) {
    setBusy(candidate.entity_id);
    setError("");
    setNotice("");
    try {
      const result = await api.testImportSwitch(candidate.entity_id, action);
      setData(
        (current) =>
          current && {
            ...current,
            candidates: current.candidates.map((c) =>
              c.entity_id === candidate.entity_id
                ? {
                    ...c,
                    state: result.state,
                    tested_actions: result.tested_actions,
                  }
                : c,
            ),
          },
      );
      setNotice(
        `${candidate.name}：${result.mode === "mock" ? "模擬" : "HA 新狀態"}已確認${result.state === "on" ? "開啟" : "關閉"}。請自行恢復需要的電源狀態。`,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "測試失敗");
    } finally {
      setBusy("");
    }
  }
  async function save() {
    setBusy("import");
    setError("");
    try {
      const result = await api.importDevices(
        selected.map(
          ({ entity_id, name, room, protected: protect, enable_control }) => ({
            entity_id,
            name,
            room,
            protected: protect,
            enable_control,
          }),
        ),
      );
      setDone(true);
      setNotice(
        `已加入 ${result.devices.length} 個${result.mode === "mock" ? "模擬" : "HA"}實體。`,
      );
      await onImported();
    } catch (e) {
      setError(e instanceof Error ? e.message : "匯入失敗");
    } finally {
      setBusy("");
    }
  }
  const rows = filterCandidates(data?.candidates ?? [], filter, search);
  const valid =
    selected.length > 0 &&
    selected.every((item) => item.name.trim() && item.room.trim());
  return (
    <dialog
      ref={dialog}
      className="device-details import-dialog"
      aria-labelledby="import-title"
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onClose();
      }}
    >
      <header className="detail-header">
        <button onClick={onClose} disabled={!!busy}>
          <ArrowLeft size={20} />
          返回
        </button>
        <h2 id="import-title">新增裝置</h2>
      </header>
      <div className="detail-content import-content">
        <div className="import-intro">
          <span className="import-icon">
            <Plus size={24} />
          </span>
          <h3>把設備加入你的家</h3>
          <p>從已連線的 Home Assistant 匯入，無需手寫設定檔。</p>
        </div>
        <ol className="import-steps" aria-label="匯入步驟">
          {["選取實體", "設定與測試", "確認匯入"].map((label, index) => (
            <li
              key={label}
              aria-current={step === index + 1 ? "step" : undefined}
            >
              <b>{index + 1}</b>
              {label}
            </li>
          ))}
        </ol>
        {data?.mode === "mock" && (
          <p className="import-hint">
            模擬模式：以下候選及操作全部為示範，不會控制真實設備。
          </p>
        )}
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        {notice && (
          <p className="detail-notice" role="status">
            {notice}
          </p>
        )}
        {step === 1 && (
          <>
            <p className="import-hint">
              第一版每個實體建立一張卡片。既有設備不會重複匯入；尚未出現的設備，請先在
              Home Assistant 完成品牌整合。
            </p>
            <div className="import-toolbar">
              <input
                aria-label="搜尋候選設備"
                placeholder="搜尋設備名稱或實體"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <button onClick={() => void reload()} disabled={loading}>
                <RefreshCw size={16} />
                重新讀取
              </button>
            </div>
            <div className="import-filters" aria-label="候選篩選">
              {(
                [
                  ["available", "可加入"],
                  ["imported", "已加入"],
                  ["unsupported", "待支援"],
                  ["all", "全部"],
                ] as [ImportFilter, string][]
              ).map(([id, label]) => (
                <button
                  key={id}
                  aria-pressed={filter === id}
                  onClick={() => setFilter(id)}
                >
                  {label}
                </button>
              ))}
            </div>
            {loading ? (
              <p className="empty-state">正在讀取 Home Assistant…</p>
            ) : (
              <>
                <ImportCandidateList
                  candidates={rows}
                  selected={selected.map((item) => item.entity_id)}
                  onToggle={(candidate) => {
                    setSelected((items) =>
                      items.some(
                        (item) => item.entity_id === candidate.entity_id,
                      )
                        ? items.filter(
                            (item) => item.entity_id !== candidate.entity_id,
                          )
                        : items.length >= 50
                          ? items
                          : [
                              ...items,
                              {
                                entity_id: candidate.entity_id,
                                name: candidate.name,
                                room: "未分類",
                                protected: true,
                                enable_control: false,
                                safe: false,
                              },
                            ],
                    );
                  }}
                />
                {rows.length === 0 && (
                  <p className="empty-state">
                    沒有符合條件的實體。可查看「已加入」或「待支援」。
                  </p>
                )}
              </>
            )}
            <div className="import-actions">
              <span>已選 {selected.length} / 50 個</span>
              <button
                className="import-primary"
                disabled={!selected.length || loading}
                onClick={() => {
                  setStep(2);
                  setError("");
                }}
              >
                下一步
              </button>
            </div>
          </>
        )}
        {step === 2 && (
          <>
            <p className="import-hint">
              <ShieldCheck size={18} />
              預設唯讀。測試會實際切換電源，請先確認設備及負載；不會自動恢復原狀。
            </p>
            {selected.map((item) => {
              const candidate = data!.candidates.find(
                (c) => c.entity_id === item.entity_id,
              )!;
              const canEnable = canEnableImportedControl(
                candidate,
                item.protected,
              );
              return (
                <section className="import-settings" key={item.entity_id}>
                  <code>{item.entity_id}</code>
                  <div className="import-fields">
                    <label>
                      裝置名稱
                      <input
                        value={item.name}
                        maxLength={120}
                        onChange={(e) =>
                          update(item.entity_id, { name: e.target.value })
                        }
                      />
                    </label>
                    <label>
                      房間
                      <input
                        value={item.room}
                        maxLength={80}
                        onChange={(e) =>
                          update(item.entity_id, { room: e.target.value })
                        }
                      />
                    </label>
                  </div>
                  <label className="import-check">
                    <input
                      type="checkbox"
                      checked={item.protected}
                      disabled={!!busy}
                      onChange={(e) =>
                        update(item.entity_id, {
                          protected: e.target.checked,
                          enable_control: false,
                          safe: false,
                        })
                      }
                    />
                    僅查看，鎖定控制（重要電源建議保留）
                  </label>
                  {candidate.can_test && !item.protected && (
                    <div className="import-test">
                      <label className="import-check">
                        <input
                          type="checkbox"
                          checked={item.safe}
                          disabled={!!busy}
                          onChange={(e) =>
                            update(item.entity_id, { safe: e.target.checked })
                          }
                        />
                        我已確認這個實體及負載可以安全切換電源
                      </label>
                      <div className="import-test-buttons">
                        {(["turn_on", "turn_off"] as const).map((action) => (
                          <button
                            key={action}
                            disabled={
                              !!busy ||
                              !item.safe ||
                              candidate.state ===
                                (action === "turn_on" ? "on" : "off")
                            }
                            onClick={() => void test(candidate, action)}
                          >
                            {candidate.tested_actions.includes(action) && (
                              <Check size={15} />
                            )}
                            {action === "turn_on" ? "測試開啟" : "測試關閉"}
                          </button>
                        ))}
                      </div>
                      <p>
                        目前：{candidate.state === "on" ? "開啟" : "關閉"} ·{" "}
                        {candidate.tested_actions.length}/2
                        個方向已確認。測試結果十分鐘內有效。
                      </p>
                      <label className="import-check">
                        <input
                          type="checkbox"
                          checked={item.enable_control && canEnable}
                          disabled={!canEnable || !!busy}
                          onChange={(e) =>
                            update(item.entity_id, {
                              enable_control: e.target.checked,
                            })
                          }
                        />
                        匯入後開放基本開關控制
                      </label>
                    </div>
                  )}
                  {!candidate.can_test && (
                    <p className="muted">
                      此實體目前僅能唯讀匯入；其他功能仍待驗證。
                    </p>
                  )}
                </section>
              );
            })}
            <div className="import-actions">
              <button disabled={!!busy} onClick={() => setStep(1)}>
                上一步
              </button>
              <button
                className="import-primary"
                disabled={!valid || !!busy}
                onClick={() => {
                  setStep(3);
                  setError("");
                }}
              >
                檢視匯入內容
              </button>
            </div>
          </>
        )}
        {step === 3 && (
          <>
            <div className="import-summary">
              {selected.map((item) => (
                <div key={item.entity_id}>
                  <strong>{item.name}</strong>
                  <span>
                    {item.room} ·{" "}
                    {item.enable_control && !item.protected
                      ? "基本開關"
                      : "唯讀／受保護"}
                  </span>
                </div>
              ))}
            </div>
            <p className="import-hint">
              匯入只新增平台卡片，不會解除配對、修改韌體或自動開關電器。進階功能仍需個別驗證。
            </p>
            <div className="import-actions">
              {done ? (
                <button className="import-primary" onClick={onClose}>
                  完成，返回裝置列表
                </button>
              ) : (
                <>
                  <button disabled={!!busy} onClick={() => setStep(2)}>
                    上一步
                  </button>
                  <button
                    className="import-primary"
                    disabled={!!busy}
                    onClick={() => void save()}
                  >
                    {busy ? "正在匯入…" : `加入 ${selected.length} 個實體`}
                  </button>
                </>
              )}
            </div>
          </>
        )}
      </div>
    </dialog>
  );
}
