import { useEffect, useRef } from "react";
import { ArrowLeft } from "lucide-react";
import type { Action, Device } from "../types/device";
import { DeviceCard } from "./DeviceCard";
import { SensorHistory } from "./SensorHistory";

export function DeviceDetails({
  device,
  readOnly,
  onClose,
  onAction,
  onInfrared,
  error,
  notice,
}: {
  device: Device;
  readOnly: boolean;
  onClose: () => void;
  onAction: (id: string, action: Action) => Promise<void>;
  onInfrared: () => void;
  error: string;
  notice: string;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const restorePosition = useRef(true);
  useEffect(() => {
    const element = dialog.current!;
    const focus = document.activeElement as HTMLElement | null;
    const position = window.scrollY;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    element.showModal();
    return () => {
      element.close();
      document.body.style.overflow = previous;
      if (restorePosition.current) {
        focus?.focus({ preventScroll: true });
        window.scrollTo({ top: position, behavior: "instant" });
      }
    };
  }, []);
  return (
    <dialog
      ref={dialog}
      className="device-details"
      aria-labelledby="device-detail-title"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget) {
          const r = event.currentTarget.getBoundingClientRect();
          if (
            event.clientX < r.left ||
            event.clientX > r.right ||
            event.clientY < r.top ||
            event.clientY > r.bottom
          )
            onClose();
        }
      }}
    >
      <header className="detail-header">
        <button onClick={onClose} aria-label="返回裝置列表">
          <ArrowLeft size={20} />
          返回
        </button>
        <h2 id="device-detail-title">{device.name}</h2>
      </header>
      <div className="detail-content">
        {error ? (
          <p className="error" role="alert">
            {error}
          </p>
        ) : notice ? (
          <p className="detail-notice" role="status">
            {notice}
          </p>
        ) : null}
        <DeviceCard device={device} readOnly={readOnly} onAction={onAction} />
        {device.capabilities.some((cap) =>
          ["temperature_sensor", "humidity_sensor"].includes(cap.name),
        ) && <SensorHistory device={device} />}
        {device.type === "gateway" && (
          <button
            className="secondary-action"
            onClick={() => {
              restorePosition.current = false;
              onInfrared();
            }}
          >
            開啟紅外線遙控
          </button>
        )}
      </div>
    </dialog>
  );
}
