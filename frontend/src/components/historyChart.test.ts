import { describe, expect, it } from "vitest";
import { chartSegments } from "./historyChart";

describe("歷史曲線", () => {
  it("未知讀值與長時間缺口不連線", () => {
    const points = [
      { at: "2026-10-16T00:00:00Z", value: 20 },
      { at: "2026-10-16T00:01:00Z", value: null },
      { at: "2026-10-16T00:02:00Z", value: 21 },
      { at: "2026-10-16T02:00:00Z", value: 22 },
    ];
    expect(chartSegments(points, 1800).map((s) => s.length)).toEqual([1, 1, 1]);
  });
});
