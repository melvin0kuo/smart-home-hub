import { useEffect, useRef, useState } from "react";
import Hls from "hls.js";
import type { Device } from "../types/device";
import { liveStreamConfig } from "./liveStream";

export function CameraPlayer({ device }: { device: Device }) {
  const [playing, setPlaying] = useState(false);
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [failureReason, setFailureReason] = useState("");
  const [latency, setLatency] = useState<number | null>(null);
  const hlsPlayer = useRef<Hls | null>(null);
  const container = useRef<HTMLDivElement>(null);
  const video = useRef<HTMLVideoElement>(null);
  const supported = device.capabilities.some(
    (c) =>
      c.name === "camera_stream" &&
      c.readable &&
      c.verification_status === "verified",
  );
  const privateMode = device.attributes.privacy_enabled === true;
  const active =
    playing && device.available && supported && !failed && !privateMode;
  useEffect(() => {
    const element = video.current;
    if (!active || !element) return;
    const url = `/api/cameras/${encodeURIComponent(device.id)}/stream`;
    let hls: Hls | undefined;
    let disposed = false;
    const play = () => {
      if (!disposed) void element.play().catch(() => {});
    };
    if (Hls.isSupported()) {
      hls = new Hls(liveStreamConfig);
      hlsPlayer.current = hls;
      hls.loadSource(url);
      hls.attachMedia(element);
      hls.on(Hls.Events.MANIFEST_PARSED, play);
      hls.on(Hls.Events.ERROR, (_, data) => {
        if (data.fatal && !disposed) {
          setFailureReason(data.details);
          setFailed(true);
        }
      });
    } else if (element.canPlayType("application/vnd.apple.mpegurl")) {
      element.src = url;
      element.addEventListener("loadedmetadata", play);
    }
    const reportLatency = () => {
      const delay = hls?.latency;
      setLatency(
        typeof delay === "number" && Number.isFinite(delay) ? delay : null,
      );
    };
    element.addEventListener("timeupdate", reportLatency);
    return () => {
      disposed = true;
      hls?.destroy();
      hlsPlayer.current = null;
      element.removeEventListener("timeupdate", reportLatency);
      element.removeEventListener("loadedmetadata", play);
      element.pause();
      element.removeAttribute("src");
      element.load();
    };
  }, [active, device.id]);
  return (
    <div className="camera-player" ref={container}>
      {active && !failed ? (
        <>
          <video
            ref={video}
            aria-label={`${device.name} 即時影像`}
            controls
            muted
            playsInline
            onPlaying={() => setLoaded(true)}
            onWaiting={() => setLoaded(false)}
            onError={() => {
              setFailureReason(
                `媒體錯誤 ${video.current?.error?.code ?? "未知"}`,
              );
              setFailed(true);
            }}
          />
          {!loaded && <p role="status">正在緩衝即時影像…</p>}
        </>
      ) : (
        <div className="camera-placeholder">
          <strong>
            {privateMode
              ? "隱私模式已開啟，鏡頭遮蔽"
              : failed
                ? "串流中斷或來源無法播放"
                : !supported
                  ? "影像待接入"
                  : !device.available
                    ? "影像來源目前不可用"
                    : "私人攝影機即時影像"}
          </strong>
          <small>
            {failed ? failureReason : "低延遲 HLS · 相容畫質預覽 · 預設靜音"}
          </small>
        </div>
      )}
      <div className="camera-actions">
        <button
          disabled={!supported || !device.available || privateMode}
          onClick={() => {
            setFailed(false);
            setLoaded(false);
            setLatency(null);
            setPlaying(failed ? true : !playing);
          }}
        >
          {playing && !failed
            ? "停止播放"
            : failed
              ? "重新播放"
              : "播放即時影像"}
        </button>
        {playing && !failed && (
          <button
            onClick={() => {
              const element = video.current;
              if (!element) return;
              const target = hlsPlayer.current?.liveSyncPosition;
              if (typeof target === "number" && Number.isFinite(target))
                element.currentTime = target;
              else if (element.seekable.length)
                element.currentTime = Math.max(
                  0,
                  element.seekable.end(element.seekable.length - 1) - 2,
                );
              void element.play().catch(() => {});
            }}
          >
            回到直播
          </button>
        )}
        {playing && !failed && (
          <button
            onClick={() =>
              void container.current?.requestFullscreen().catch(() => {})
            }
          >
            全螢幕
          </button>
        )}
      </div>
      <small>
        {active && latency !== null
          ? `距串流最新位置約 ${latency.toFixed(1)} 秒；`
          : "影像可能延遲數秒；"}
        離開頁面或停止播放即停止下載。
      </small>
    </div>
  );
}
