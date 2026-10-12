import Hls from "hls.js";
import { expect, it } from "vitest";
import { liveStreamConfig } from "./liveStream";

it("低延遲設定可由 Hls.js 接受，並以秒數限制直播落後", () => {
  const hls = new Hls(liveStreamConfig);
  expect(hls.config.lowLatencyMode).toBe(true);
  expect(hls.config.liveSyncDuration).toBeLessThanOrEqual(3);
  expect(hls.config.liveMaxLatencyDuration).toBeGreaterThan(
    hls.config.liveSyncDuration!,
  );
  expect(hls.config.liveMaxLatencyDuration).toBeLessThanOrEqual(8);
  hls.destroy();
});
