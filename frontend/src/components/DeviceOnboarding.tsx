import { useEffect, useState } from "react";
import {
  ArrowLeft,
  ArrowUpRight,
  Radio,
  RefreshCw,
  Search,
} from "lucide-react";
import { api } from "../services/api";
import { searchIntegrations } from "../services/onboarding";
import type { IntegrationOption, OnboardingData } from "../types/onboarding";

export function OnboardingCatalog({
  options,
  onSelect,
}: {
  options: IntegrationOption[];
  onSelect: (option: IntegrationOption) => void;
}) {
  return (
    <div className="onboarding-catalog">
      {options.map((option) => (
        <button
          key={option.domain}
          className="onboarding-option"
          onClick={() => onSelect(option)}
        >
          <span className="onboarding-option-label">
            <strong>{option.name}</strong>
            <small>{option.domain}</small>
          </span>
          <span className="onboarding-status">
            {option.available ? "可進行設定" : "此 HA 尚未提供"}
          </span>
        </button>
      ))}
    </div>
  );
}

export function OnboardingGuide({
  option,
  mock,
  onReturn,
}: {
  option: IntegrationOption;
  mock: boolean;
  onReturn: () => void;
}) {
  return (
    <section className="onboarding-guide" aria-label={`${option.name}設定指引`}>
      <h3>{option.name}</h3>
      <ol className="onboarding-checklist">
        <li>
          <strong>確認準備條件</strong>
          <p>{option.requirements}</p>
        </li>
        <li>
          <strong>在 Home Assistant 完成配對</strong>
          <p>{option.instructions}</p>
        </li>
        <li>
          <strong>回來讀取設備</strong>
          <p>
            設定完成後回到這裡選取實體。目錄可設定不代表所有型號與功能已驗證。
          </p>
        </li>
      </ol>
      {!option.available && (
        <p className="import-hint">
          此 HA 尚未提供這個設定流程，請先依文件安裝所需整合或服務。
        </p>
      )}
      {mock && (
        <p className="import-hint">模擬模式：只示範指引，不會建立真實配對。</p>
      )}
      <div className="onboarding-links">
        {!mock && option.available && option.setup_url && (
          <a
            className="import-primary"
            href={option.setup_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            在 HA 開始設定 <ArrowUpRight size={16} />
          </a>
        )}
        {option.documentation_url && (
          <a
            href={option.documentation_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            查看整合文件 <ArrowUpRight size={16} />
          </a>
        )}
      </div>
      <p className="import-hint">
        登入與權限授予在 HA
        或品牌官方頁面進行；此頁不收集品牌密碼。已探索的設備請於
        HA「已發現」卡片按設定，避免重複建立流程。
      </p>
      <button className="import-primary" onClick={onReturn}>
        配對完成，讀取設備
      </button>
    </section>
  );
}

export function DeviceOnboarding({ onPaired }: { onPaired: () => void }) {
  const [data, setData] = useState<OnboardingData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<"all" | "protocol">("all");
  const [selected, setSelected] = useState<IntegrationOption | null>(null);
  const [limit, setLimit] = useState(40);
  useEffect(() => {
    let active = true;
    api
      .onboarding()
      .then((result) => {
        if (active) setData(result);
      })
      .catch((e) => {
        if (active)
          setError(e instanceof Error ? e.message : "無法讀取整合目錄");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);
  async function reload() {
    setLoading(true);
    setError("");
    try {
      setData(await api.onboarding());
    } catch (e) {
      setError(e instanceof Error ? e.message : "讀取失敗");
    } finally {
      setLoading(false);
    }
  }
  const rows = searchIntegrations(data?.catalog ?? [], query, category);
  if (selected)
    return (
      <>
        <button onClick={() => setSelected(null)}>
          <ArrowLeft size={16} />
          返回整合目錄
        </button>
        {data?.local_only_url && <LocalUrlNotice />}
        <OnboardingGuide
          option={selected}
          mock={data?.mode === "mock"}
          onReturn={onPaired}
        />
      </>
    );
  return (
    <div className="onboarding-page">
      <div className="onboarding-explainer">
        <Radio size={24} />
        <div>
          <strong>先配對，再加入你的家</strong>
          <p>
            探索附近設備，或搜尋品牌與協定。沿用這台 Home Assistant
            的整合目錄，完成設定後自動讀取可匯入實體。
          </p>
        </div>
      </div>
      {data?.mode === "mock" && (
        <p className="import-hint">
          模擬模式：以下為示範目錄，沒有掃描或配對真實設備。
        </p>
      )}
      {data?.local_only_url && <LocalUrlNotice />}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {data?.warnings.map((message) => (
        <p className="import-hint" key={message}>
          {message}
        </p>
      ))}
      <section className="onboarding-discovery">
        <div className="onboarding-heading">
          <h3>HA 已探索，等待設定</h3>
          <button disabled={loading} onClick={() => void reload()}>
            <RefreshCw size={16} />
            重新探索
          </button>
        </div>
        <p className="import-hint">
          讀取 HA 的探索結果，不執行全網路掃描，也不自動配對。
        </p>
        {loading ? (
          <p role="status">正在讀取目錄與探索結果…</p>
        ) : data?.discovered.length ? (
          data.discovered.map((device) => (
            <div className="onboarding-discovered" key={device.id}>
              <span>
                <strong>{device.name}</strong>
                <small>{device.source} · 請到 HA「已發現」卡片設定</small>
              </span>
              {device.setup_url && (
                <a
                  href={device.setup_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  開啟 HA <ArrowUpRight size={16} />
                </a>
              )}
            </div>
          ))
        ) : (
          <p className="import-hint">
            {data?.discovery_status === "unavailable"
              ? "探索暫時不可用，可改從下方目錄設定。"
              : "目前沒有等待設定的探索結果；可從下方搜尋品牌或協定。"}
          </p>
        )}
        <button className="import-primary" onClick={onPaired}>
          配對完成，讀取設備
        </button>
      </section>
      <section>
        <h3>搜尋品牌與整合</h3>
        <label className="onboarding-search">
          <Search size={18} />
          <input
            aria-label="搜尋品牌或協定"
            placeholder="例如 Tapo、小米、Matter、Shelly…"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setLimit(40);
            }}
          />
        </label>
        <div className="import-filters">
          <button
            aria-pressed={category === "all"}
            onClick={() => {
              setCategory("all");
              setLimit(40);
            }}
          >
            所有整合
          </button>
          <button
            aria-pressed={category === "protocol"}
            onClick={() => {
              setCategory("protocol");
              setLimit(40);
            }}
          >
            常見協定
          </button>
        </div>
        <p className="import-hint">
          {rows.length} 個結果 · 來源：
          {data?.catalog_status === "available"
            ? "這台 HA 的動態整合目錄"
            : data?.mode === "mock"
              ? "模擬示範"
              : "參考指引"}
          。搜尋整合名稱與別名，尚不提供完整產品型號查詢。
        </p>
        <OnboardingCatalog
          options={rows.slice(0, limit)}
          onSelect={setSelected}
        />
        {!loading && rows.length === 0 && (
          <p className="empty-state">
            找不到符合項目。可改搜尋品牌英文名稱、協定，或查閱下方資料庫確認相容性。
          </p>
        )}
        {rows.length > limit && (
          <button onClick={() => setLimit((value) => value + 40)}>
            顯示更多（目前 {limit} / {rows.length}）
          </button>
        )}
      </section>
      <section className="onboarding-databases">
        <h3>查詢產品相容性</h3>
        <p className="import-hint">
          資料庫可協助辨識型號；是否能控制仍需相符的整合與硬體。
        </p>
        <a
          href="https://www.zigbee2mqtt.io/supported-devices/"
          target="_blank"
          rel="noopener noreferrer"
        >
          Zigbee2MQTT 裝置庫 <ArrowUpRight size={16} />
        </a>
        <a
          href="https://csa-iot.org/csa-iot_products/"
          target="_blank"
          rel="noopener noreferrer"
        >
          Matter／Zigbee 認證查詢 <ArrowUpRight size={16} />
        </a>
        <a
          href="https://devices.esphome.io/"
          target="_blank"
          rel="noopener noreferrer"
        >
          ESPHome 裝置庫 <ArrowUpRight size={16} />
        </a>
      </section>
    </div>
  );
}

function LocalUrlNotice() {
  return (
    <p className="import-hint onboarding-url-notice">
      目前 HA 設定連結使用本機網址，手機／平板無法連到這台電腦的
      localhost。請在後端 .env 設定手機可存取的
      HA_BROWSER_URL，重新啟動後再配對；這不影響既有設備控制。
    </p>
  );
}
