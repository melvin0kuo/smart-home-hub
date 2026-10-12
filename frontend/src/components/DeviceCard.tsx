import { useState } from "react";
import {
  Camera,
  Droplets,
  LampDesk,
  Plug,
  Radio,
  Wind,
  Thermometer,
  ArrowUpRight,
} from "lucide-react";
import { canControl, type Action, type Device } from "../types/device";
import { CameraPlayer } from "./CameraPlayer";
import { DehumidifierControls } from "./DehumidifierControls";
import { DiffuserSettings } from "./DiffuserSettings";
import { CameraControls } from "./CameraControls";
import { SensorReadings } from "./SensorReadings";
const icons: Record<string, typeof Plug> = {
  power_strip: Plug,
  light: LampDesk,
  sensor: Thermometer,
  camera: Camera,
  gateway: Radio,
  diffuser: Wind,
  dehumidifier: Droplets,
};
function Toggle({
  checked,
  label,
  disabled,
  onClick,
}: {
  checked: boolean;
  label: string;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      className={`toggle ${checked ? "on" : ""}`}
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={onClick}
    >
      <span />
    </button>
  );
}
function RangeControl({
  device,
  name,
  label,
  attribute,
  onAction,
  disabled,
}: {
  device: Device;
  name: string;
  label: string;
  attribute: "brightness" | "color_temperature";
  onAction: (a: Action) => Promise<void>;
  disabled: boolean;
}) {
  const cap = device.capabilities.find((c) => c.name === name)!,
    reportedValue = device.attributes[attribute],
    hasReportedValue =
      typeof reportedValue === "number" && Number.isFinite(reportedValue),
    current = hasReportedValue ? reportedValue : (cap.minimum ?? 0);
  const [draft, setDraft] = useState<number | null>(null),
    value = draft ?? current;
  const commit = () => {
    if (hasReportedValue && draft !== null && draft !== current)
      void onAction({
        action:
          attribute === "brightness"
            ? "set_brightness"
            : "set_color_temperature",
        parameters: { value: draft },
      }).finally(() => setDraft(null));
  };
  return (
    <label className="range-label">
      <span>
        {label}
        <strong>
          {hasReportedValue ? `${value}${cap.unit ?? ""}` : "尚未回報"}
        </strong>
      </span>
      <input
        aria-label={label}
        type="range"
        min={cap.minimum}
        max={cap.maximum}
        step={name === "brightness" ? 1 : 50}
        value={value}
        disabled={disabled || !hasReportedValue}
        onChange={(e) => setDraft(Number(e.target.value))}
        onPointerUp={commit}
        onKeyUp={commit}
      />
    </label>
  );
}
export function DeviceCard({
  device,
  onAction,
  readOnly,
  compactCamera = false,
  onOpenCamera,
}: {
  device: Device;
  onAction: (id: string, a: Action) => Promise<void>;
  readOnly: boolean;
  compactCamera?: boolean;
  onOpenCamera?: () => void;
}) {
  const Icon = icons[device.type] ?? Plug,
    [busy, setBusy] = useState(false);
  const action = async (a: Action) => {
    if (busy) return;
    setBusy(true);
    try {
      await onAction(device.id, a);
    } finally {
      setBusy(false);
    }
  };
  const label =
    device.online === null ? "待確認" : device.online ? "在線" : "離線";
  return (
    <article
      data-device-id={device.id}
      className={`device-card ${device.type === "camera" && !compactCamera ? "camera-card" : ""} ${device.type === "power_strip" ? "wide" : ""} ${device.available ? "" : "unavailable"}`}
    >
      <header>
        <div className={`device-icon ${device.type}`}>
          <Icon size={23} />
        </div>
        <span className={`status ${device.online ? "live" : ""}`}>
          <i />
          {label}
          {device.stale ? " · 過期" : ""}
        </span>
      </header>
      <div className="card-title">
        <div>
          <p>
            {device.room}
            <span> ／ {device.manufacturer}</span>
          </p>
          <h3>{device.name}</h3>
        </div>
        {device.type !== "power_strip" &&
          device.type !== "diffuser" &&
          canControl(device, "switch") && (
            <Toggle
              label={device.name}
              checked={device.state === "on"}
              disabled={busy || readOnly}
              onClick={() =>
                void action({
                  action: device.state === "on" ? "turn_off" : "turn_on",
                })
              }
            />
          )}
      </div>
      <p className="model">
        {device.model}
        <span>
          {device.source === "mock"
            ? "模擬設備"
            : device.source === "bluetooth"
              ? "藍牙直連"
              : "Home Assistant"}
        </span>
      </p>
      {device.capabilities.some(
        (c) => c.name === "switch" && c.target === "main",
      ) &&
        !canControl(device, "switch") && (
          <p className="detail-notice">
            {!device.available || device.stale
              ? "電源狀態待確認"
              : device.state === "on"
                ? "電源已開啟"
                : device.state === "off"
                  ? "電源已關閉"
                  : "電源狀態待確認"}{" "}
            · 唯讀
          </p>
        )}
      {device.type === "power_strip" && (
        <div className="outlets">
          {device.attributes.outlets?.map((o) => (
            <div key={o.id} className={o.state === "on" ? "active" : ""}>
              <Plug size={17} />
              <div className="outlet-info">
                <strong>{o.name}</strong>
                <small>
                  {o.state === "on"
                    ? "已開啟"
                    : o.state === "off"
                      ? "已關閉"
                      : o.state === "always_on"
                        ? "一般插座"
                        : "狀態待確認"}
                </small>
                {o.control_note && <small>{o.control_note}</small>}
              </div>
              {canControl(device, "switch", o.id) ? (
                <Toggle
                  checked={o.state === "on"}
                  label={o.name}
                  disabled={busy || readOnly}
                  onClick={() =>
                    void action({
                      action: o.state === "on" ? "turn_off" : "turn_on",
                      target: o.id,
                    })
                  }
                />
              ) : (
                <span>
                  {o.control_note
                    ? "已鎖定"
                    : o.state === "always_on"
                      ? "一般插座"
                      : "未開放"}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
      {device.type === "light" && (
        <div className="light-controls">
          {canControl(device, "brightness") && (
            <RangeControl
              device={device}
              name="brightness"
              label="亮度"
              attribute="brightness"
              onAction={action}
              disabled={busy || readOnly}
            />
          )}{" "}
          {canControl(device, "color_temperature") && (
            <RangeControl
              device={device}
              name="color_temperature"
              label="色溫"
              attribute="color_temperature"
              onAction={action}
              disabled={busy || readOnly}
            />
          )}
        </div>
      )}
      {device.type === "sensor" && <SensorReadings device={device} />}
      {device.type === "dehumidifier" && (
        <div className="sensor-values">
          <div>
            <Thermometer size={17} />
            <strong>
              {device.attributes.temperature ?? "—"}
              <small>°C</small>
            </strong>
            <span>室內溫度</span>
          </div>
          <div>
            <Droplets size={17} />
            <strong>
              {device.attributes.humidity ?? "—"}
              <small>%</small>
            </strong>
            <span>相對濕度</span>
          </div>
          <p
            role={
              device.attributes.water_tank_full === true ? "alert" : undefined
            }
          >
            <Droplets size={15} />
            {device.attributes.water_tank_full === true
              ? "水箱已滿，請檢查並倒水"
              : device.attributes.water_tank_full === false
                ? "水箱未滿"
                : "水箱狀態待確認"}
          </p>
        </div>
      )}
      {device.type === "dehumidifier" && (
        <DehumidifierControls
          device={device}
          disabled={busy || readOnly}
          onAction={action}
        />
      )}
      {device.type === "dehumidifier" &&
        device.capabilities.some(
          (c) =>
            c.name === "switch" &&
            c.target === "swing" &&
            c.writable &&
            ["verified", "mock"].includes(c.verification_status),
        ) && (
          <div className="privacy-control">
            <div>
              <strong>上下自動擺風</strong>
              <p>
                {device.attributes.vertical_swing === true
                  ? "導風板上下擺動"
                  : device.attributes.vertical_swing === false
                    ? "已停止擺動"
                    : "風向狀態待確認"}
              </p>
            </div>
            <Toggle
              label="上下自動擺風"
              checked={device.attributes.vertical_swing === true}
              disabled={
                busy ||
                readOnly ||
                device.attributes.vertical_swing == null ||
                !canControl(device, "switch", "swing")
              }
              onClick={() =>
                void action({
                  action: device.attributes.vertical_swing
                    ? "turn_off"
                    : "turn_on",
                  target: "swing",
                })
              }
            />
          </div>
        )}
      {device.type === "camera" && compactCamera ? (
        <div className="camera-summary">
          <Camera size={32} />
          <p>
            {device.attributes.privacy_enabled === true
              ? "隱私模式已開啟"
              : device.attributes.privacy_enabled === false
                ? "鏡頭已啟用，影像預設不播放"
                : "隱私狀態待確認"}
          </p>
          <button className="secondary-action" onClick={onOpenCamera}>
            開啟攝影機
          </button>
        </div>
      ) : device.type === "camera" ? (
        <div className="camera-workspace">
          {device.type === "camera" &&
            device.capabilities.some((c) => c.name === "camera_privacy") && (
              <div className="privacy-control">
                <div>
                  <strong>隱私模式</strong>
                  <p>
                    {device.attributes.privacy_enabled === true
                      ? "已開啟 · 鏡頭遮蔽"
                      : device.attributes.privacy_enabled === false
                        ? "已關閉 · 可觀看影像"
                        : "狀態待確認"}
                  </p>
                  <small>關閉隱私模式會啟用鏡頭；不會自動播放。</small>
                </div>
                <Toggle
                  label="隱私模式"
                  checked={device.attributes.privacy_enabled === true}
                  disabled={
                    busy ||
                    readOnly ||
                    !device.attributes.privacy_available ||
                    !canControl(device, "camera_privacy", "privacy")
                  }
                  onClick={() =>
                    void action({
                      action: device.attributes.privacy_enabled
                        ? "disable_privacy"
                        : "enable_privacy",
                      target: "privacy",
                    })
                  }
                />
              </div>
            )}
          {device.type === "camera" &&
          device.capabilities.some(
            (c) =>
              c.name === "camera_stream" &&
              c.verification_status === "verified",
          ) ? (
            <CameraPlayer
              key={`${device.id}-${device.attributes.privacy_enabled}`}
              device={device}
            />
          ) : (
            device.type === "camera" && (
              <div className="camera-placeholder">
                <Camera size={30} />
                <span>自製平台串流尚未接入</span>
                <small>
                  {device.source === "mock"
                    ? "模擬設備 · 串流與 PTZ 待實機驗證"
                    : device.available
                      ? "HA 狀態已同步 · PTZ 尚未開放"
                      : "HA 影像實體目前不可用"}
                </small>
              </div>
            )
          )}
          {device.type === "camera" && (
            <CameraControls device={device} readOnly={readOnly} />
          )}
        </div>
      ) : null}
      {device.type === "gateway" && (
        <div className="gateway-visual">
          <Radio size={36} />
          <div>
            <strong>
              {device.source === "mock"
                ? "模擬網關 · 能力待驗證"
                : "網關狀態已同步"}
            </strong>
            <span>可用指令請至紅外線遙控頁面查看</span>
          </div>
        </div>
      )}
      {device.type === "diffuser" &&
        (device.capabilities.some(
          (c) =>
            c.name === "switch" &&
            c.writable &&
            ["verified", "mock"].includes(c.verification_status),
        ) ? (
          <div className="diffuser-controls">
            {(["main", "light"] as const).map((target) => {
              const title = target === "main" ? "擴香" : "香氛燈光";
              const value =
                target === "main"
                  ? device.state === "unknown"
                    ? null
                    : device.state === "on"
                  : device.attributes.light_on;
              return (
                <div className="privacy-control" key={target}>
                  <div>
                    <strong>{title}</strong>
                    <p>
                      {value == null
                        ? "等待裝置回報"
                        : value
                          ? "已開啟"
                          : "已關閉"}
                    </p>
                  </div>
                  <Toggle
                    label={title}
                    checked={value === true}
                    disabled={
                      busy ||
                      readOnly ||
                      value == null ||
                      !canControl(device, "switch", target)
                    }
                    onClick={() =>
                      void action({
                        action: value ? "turn_off" : "turn_on",
                        target,
                      })
                    }
                  />
                </div>
              );
            })}
            <p className="model">電量 {device.attributes.battery ?? "—"}%</p>
            <DiffuserSettings
              device={device}
              disabled={busy || readOnly}
              onAction={action}
            />
            <p className="model" role="status">
              {busy
                ? "正在等待裝置確認…"
                : !device.available
                  ? "藍牙未連線，正在重試"
                  : "設定以裝置回報為準"}
            </p>
          </div>
        ) : (
          <div className="support-placeholder">
            <Wind size={30} />
            <strong>保留紀錄，等待整合</strong>
            <span>尚未提供擴香與燈光控制</span>
          </div>
        ))}
      <footer>
        {device.type === "power_strip" ? (
          <>
            <span>
              <i className="green-dot" />
              {device.capabilities.some((c) => c.name === "power_monitoring")
                ? "全機功率"
                : "用電監測尚未確認"}
            </span>
            <strong>
              {device.attributes.power_w ?? "—"}{" "}
              {device.attributes.power_w !== undefined && <small>W</small>}
            </strong>
          </>
        ) : (
          <>
            <span>
              {device.type === "light"
                ? device.source === "mock"
                  ? "燈光設定為模擬範圍"
                  : device.capabilities.some(
                        (c) =>
                          c.writable && c.verification_status === "verified",
                      )
                    ? "已驗證的燈光控制"
                    : "唯讀狀態 · 控制待驗證"
                : "功能依驗證結果開放"}
            </span>
            <ArrowUpRight size={15} />
          </>
        )}
      </footer>
      {(device.integration_note ?? device.attributes.note) && (
        <details className="device-note">
          <summary>整合資訊與限制</summary>
          <p>{device.integration_note ?? device.attributes.note}</p>
        </details>
      )}
    </article>
  );
}
