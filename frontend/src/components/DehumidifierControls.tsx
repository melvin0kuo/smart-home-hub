import { canControl, type Device, type Action } from "../types/device";
const labels: Record<string, string> = {
  Complete: "雙效",
  Continuous: "除濕（連續）",
  Dry: "乾衣",
  Purify: "空氣清淨",
  Automatic: "智慧（自動）",
  Manual: "手動",
  Quiet: "睡眠",
  Low: "低速",
  Middle: "中速",
  High: "高速",
  Auto: "自動",
};
export function DehumidifierControls({
  device,
  disabled,
  onAction,
}: {
  device: Device;
  disabled: boolean;
  onAction: (action: Action) => Promise<void>;
}) {
  const humidity = device.capabilities.find(
    (c) => c.name === "target_humidity",
  );
  const adjustable =
    device.state === "on" &&
    device.attributes.mode === "Complete" &&
    device.attributes.operative_mode === "Manual";
  return (
    <div className="light-controls dehumidifier-controls">
      {(["mode", "operative_mode", "fan_speed"] as const).map((name) => {
        const cap = device.capabilities.find((c) => c.name === name);
        if (!cap || !canControl(device, name, cap.target)) return null;
        return (
          <label className="range-label" key={name}>
            <span>
              {name === "mode"
                ? "功能模式"
                : name === "fan_speed"
                  ? "風速"
                  : "運轉模式"}
            </span>
            <select
              aria-label={
                name === "mode"
                  ? "功能模式"
                  : name === "fan_speed"
                    ? "風速"
                    : "運轉模式"
              }
              value={device.attributes[name] ?? ""}
              disabled={
                disabled ||
                (name === "fan_speed" &&
                  (device.state !== "on" ||
                    device.attributes.operative_mode !== "Manual")) ||
                (name === "operative_mode" && device.attributes.mode === "Dry")
              }
              onChange={(e) =>
                void onAction({
                  action:
                    name === "mode"
                      ? "set_mode"
                      : name === "fan_speed"
                        ? "set_fan_speed"
                        : "set_operative_mode",
                  target: cap.target,
                  parameters: { value: e.target.value },
                })
              }
            >
              <option value="" disabled>
                尚未回報
              </option>
              {name === "fan_speed" &&
                device.attributes.fan_speed === "Auto" && (
                  <option value="Auto" disabled>
                    自動（依運轉模式）
                  </option>
                )}
              {cap.options?.map((value) => (
                <option key={value} value={value}>
                  {labels[value] ?? value}
                </option>
              ))}
            </select>
          </label>
        );
      })}
      {humidity && canControl(device, "target_humidity", humidity.target) && (
        <label className="range-label">
          <span>
            目標濕度<strong>{device.attributes.target_humidity ?? "—"}%</strong>
          </span>
          <select
            aria-label="目標濕度"
            value={device.attributes.target_humidity ?? ""}
            disabled={
              disabled ||
              !adjustable ||
              device.attributes.target_humidity == null
            }
            onChange={(e) =>
              void onAction({
                action: "set_target_humidity",
                target: humidity.target,
                parameters: { value: Number(e.target.value) },
              })
            }
          >
            <option value="" disabled>
              尚未回報
            </option>
            {Array.from(
              {
                length:
                  Math.floor(
                    ((humidity.maximum ?? 85) - (humidity.minimum ?? 35)) /
                      (humidity.step ?? 5),
                  ) + 1,
              },
              (_, i) => (humidity.minimum ?? 35) + i * (humidity.step ?? 5),
            ).map((n) => (
              <option value={n} key={n}>
                {n}%
              </option>
            ))}
          </select>
          {!adjustable && <small>請先開機並選擇雙效＋手動模式</small>}
        </label>
      )}
    </div>
  );
}
