import { useState } from "react";
import { canControl, type Action, type Device } from "../types/device";

export function DiffuserSettings({
  device,
  disabled,
  onAction,
}: {
  device: Device;
  disabled: boolean;
  onAction: (action: Action) => Promise<void>;
}) {
  const [brightness, setBrightness] = useState<number | null>(null);
  const [color, setColor] = useState<string | null>(null);
  const reportedColor = device.attributes.color;
  const currentColor =
    typeof reportedColor === "number"
      ? `#${reportedColor.toString(16).padStart(6, "0")}`
      : null;
  const reportedBrightness = device.attributes.brightness;
  const settings = [
    {
      name: "diffusion_duration",
      label: "出香時長",
      field: "diffusion_seconds",
      action: "set_diffusion_duration",
    },
    {
      name: "diffusion_interval",
      label: "出香間隔",
      field: "diffusion_interval",
      action: "set_diffusion_interval",
    },
  ] as const;
  const verified = (name: string) =>
    device.capabilities.some(
      (c) =>
        c.name === name && c.writable && c.verification_status === "verified",
    );
  return (
    <div className="diffuser-settings">
      {settings.map((setting) => {
        const cap = device.capabilities.find((c) => c.name === setting.name);
        if (!cap || !verified(setting.name)) return null;
        const options = Array.from(
          {
            length:
              Math.floor(
                ((cap.maximum ?? 0) - (cap.minimum ?? 0)) / (cap.step ?? 1),
              ) + 1,
          },
          (_, i) => (cap.minimum ?? 0) + i * (cap.step ?? 1),
        );
        const value = device.attributes[setting.field];
        return (
          <label className="range-label" key={setting.name}>
            <span>{setting.label}</span>
            <select
              aria-label={setting.label}
              value={value ?? ""}
              disabled={
                disabled || value == null || !canControl(device, setting.name)
              }
              onChange={(e) =>
                void onAction({
                  action: setting.action,
                  parameters: { value: Number(e.target.value) },
                })
              }
            >
              <option value="" disabled>
                等待裝置回報
              </option>
              {options.map((option) => (
                <option key={option} value={option}>
                  {option} {cap.unit}
                </option>
              ))}
            </select>
          </label>
        );
      })}
      {verified("brightness") && (
        <div className="diffuser-setting">
          <label className="range-label">
            <span>
              氛圍燈亮度{" "}
              <strong>
                {reportedBrightness == null
                  ? "尚未回報"
                  : `${brightness ?? reportedBrightness}%`}
              </strong>
            </span>
            <input
              aria-label="氛圍燈亮度"
              type="range"
              min={1}
              max={100}
              step={1}
              value={brightness ?? reportedBrightness ?? 1}
              disabled={
                disabled ||
                reportedBrightness == null ||
                !canControl(device, "brightness", "light")
              }
              onChange={(e) => setBrightness(Number(e.target.value))}
            />
          </label>
          <button
            className="secondary-action"
            disabled={
              disabled ||
              brightness == null ||
              !canControl(device, "brightness", "light")
            }
            onClick={() =>
              void onAction({
                action: "set_brightness",
                target: "light",
                parameters: { value: brightness! },
              }).finally(() => setBrightness(null))
            }
          >
            套用亮度
          </button>
        </div>
      )}
      {verified("color") && (
        <div className="diffuser-setting">
          <label className="range-label">
            <span>
              氛圍燈顏色{" "}
              <strong>
                {currentColor
                  ? (color ?? currentColor).toUpperCase()
                  : "尚未回報"}
              </strong>
            </span>
            <input
              aria-label="氛圍燈顏色"
              type="color"
              value={color ?? currentColor ?? "#000000"}
              disabled={
                disabled ||
                currentColor == null ||
                !canControl(device, "color", "light")
              }
              onChange={(e) => setColor(e.target.value)}
            />
          </label>
          <button
            className="secondary-action"
            disabled={
              disabled || color == null || !canControl(device, "color", "light")
            }
            onClick={() =>
              void onAction({
                action: "set_color",
                target: "light",
                parameters: { value: parseInt(color!.slice(1), 16) },
              }).finally(() => setColor(null))
            }
          >
            套用顏色
          </button>
        </div>
      )}
      <p className="model">定時排程尚未接入；目前不會建立或變更米家定時。</p>
    </div>
  );
}
