import { useState } from "react";
import type { Device } from "../types/device";
import { api } from "../services/api";

export function CameraControls({
  device,
  readOnly,
}: {
  device: Device;
  readOnly: boolean;
}) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const supported = device.capabilities.some(
    (c) =>
      c.name === "camera_ptz" &&
      c.writable &&
      c.verification_status === "verified",
  );
  if (!supported) return null;
  const blocked =
    readOnly ||
    busy ||
    !device.available ||
    device.attributes.privacy_enabled !== false ||
    !device.attributes.privacy_available;
  async function move(direction: "left" | "right" | "up" | "down" | "stop") {
    setBusy(true);
    try {
      const result = await api.cameraPtz(device.id, direction);
      setMessage(result.message);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "旋轉控制失敗");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div aria-label="攝影機方向控制">
      <div className="camera-actions">
        {(
          [
            ["left", "向左"],
            ["up", "向上"],
            ["down", "向下"],
            ["right", "向右"],
          ] as const
        ).map(([direction, label]) => (
          <button
            key={direction}
            disabled={blocked}
            onClick={() => void move(direction)}
          >
            {label}
          </button>
        ))}
        <button
          disabled={readOnly || device.attributes.privacy_enabled === true}
          onClick={() => void move("stop")}
        >
          停止旋轉
        </button>
      </div>
      <small>每次移動 1 秒並自動停止；隱私模式開啟時停用方向控制。</small>
      {message && <p role="status">{message}</p>}
    </div>
  );
}
