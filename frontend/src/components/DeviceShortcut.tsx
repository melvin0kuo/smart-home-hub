import { useState } from "react";
import {
  Camera,
  Droplets,
  LampDesk,
  Plug,
  Radio,
  Wind,
  Thermometer,
  ChevronRight,
} from "lucide-react";
import { canControl, type Action, type Device } from "../types/device";

export function DeviceShortcut({
  device,
  readOnly,
  onOpen,
  onAction,
}: {
  device: Device;
  readOnly: boolean;
  onOpen: () => void;
  onAction: (id: string, action: Action) => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const Icon =
    (
      {
        camera: Camera,
        dehumidifier: Droplets,
        light: LampDesk,
        power_strip: Plug,
        gateway: Radio,
        diffuser: Wind,
        sensor: Thermometer,
      } as Record<string, typeof Plug>
    )[device.type] ?? Plug;
  const verified = (target: string) =>
    device.capabilities.some(
      (c) =>
        c.name === "switch" &&
        c.target === target &&
        c.writable &&
        ["verified", "mock"].includes(c.verification_status),
    );
  const outlet =
    device.type === "power_strip"
      ? device.attributes.outlets?.find(
          (o) => !o.control_note?.includes("鎖定") && verified(o.id),
        )
      : undefined;
  const controls =
    device.type === "power_strip"
      ? outlet
        ? [{ target: outlet.id, label: outlet.name, state: outlet.state }]
        : []
      : verified("main")
        ? [
            {
              target: "main",
              label: device.type === "diffuser" ? "擴香" : "電源",
              state: device.state,
            },
          ]
        : [];
  if (device.type === "diffuser" && verified("light"))
    controls.push({
      target: "light",
      label: "燈光",
      state:
        device.attributes.light_on == null
          ? "unknown"
          : device.attributes.light_on
            ? "on"
            : "off",
    });
  const status =
    !device.available || device.stale
      ? "目前不可操作"
      : device.state === "on"
        ? "已開啟"
        : device.state === "off"
          ? "已關閉"
          : "狀態已同步";
  const summary =
    device.type === "diffuser"
      ? `電量 ${device.attributes.battery ?? "—"}% · 燈光${device.attributes.light_on == null ? "待確認" : device.attributes.light_on ? "開" : "關"}`
      : ["sensor", "dehumidifier"].includes(device.type)
        ? device.attributes.water_tank_full === true
          ? "水箱已滿，請檢查並倒水"
          : `${device.attributes.temperature ?? "—"}°C · 濕度 ${device.attributes.humidity ?? "—"}%`
        : device.type === "camera"
          ? device.attributes.privacy_enabled === true
            ? "隱私模式已開啟"
            : "點選查看影像與控制"
          : device.type === "power_strip"
            ? "獨立插孔 · 重要電源已鎖定"
            : device.type === "gateway"
              ? "子設備與紅外線遙控"
              : status;
  return (
    <article className="device-shortcut" data-device-id={device.id}>
      <button
        className="shortcut-open"
        onClick={onOpen}
        aria-label={`開啟${device.name}詳細控制`}
        aria-haspopup="dialog"
      >
        <div className="shortcut-top">
          <span className={`device-icon ${device.type}`}>
            <Icon size={22} />
          </span>
          <span
            className={`status ${device.online && !device.stale ? "live" : ""}`}
          >
            <i />
            {device.stale
              ? "待同步"
              : device.online == null
                ? "待確認"
                : device.online
                  ? "在線"
                  : "離線"}
          </span>
        </div>
        <small>
          {device.room} · {device.manufacturer}
        </small>
        <h3>{device.name}</h3>
        <p>{summary}</p>
        <span className="shortcut-detail">
          詳細控制 <ChevronRight size={15} />
        </span>
      </button>
      <div className="shortcut-actions">
        {controls.length ? (
          controls.map((control) => (
            <label key={control.target}>
              <span>{control.label}</span>
              <button
                className={`toggle ${control.state === "on" ? "on" : ""}`}
                role="switch"
                aria-label={`${device.name} ${control.label}`}
                aria-checked={control.state === "on"}
                disabled={
                  readOnly ||
                  busy ||
                  !["on", "off"].includes(control.state) ||
                  !canControl(device, "switch", control.target)
                }
                onClick={async () => {
                  if (busy) return;
                  setBusy(true);
                  try {
                    await onAction(device.id, {
                      action: control.state === "on" ? "turn_off" : "turn_on",
                      target: control.target,
                    });
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                <span />
              </button>
            </label>
          ))
        ) : (
          <span className="shortcut-hint">
            {device.type === "camera" ? "開啟詳情後播放" : "點選卡片查看詳情"}
          </span>
        )}
      </div>
    </article>
  );
}
