import type { HlsConfig } from "hls.js";

// 以秒數設定直播同步，避免攝影機較長的完整片段放大預設延遲。
export const liveStreamConfig: Partial<HlsConfig> = {
  lowLatencyMode: true,
  liveSyncDuration: 2,
  liveMaxLatencyDuration: 6,
  maxLiveSyncPlaybackRate: 1.2,
  backBufferLength: 5,
  maxBufferLength: 6,
  maxMaxBufferLength: 12,
};
