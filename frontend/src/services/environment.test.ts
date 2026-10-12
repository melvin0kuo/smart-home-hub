import { expect, it } from "vitest";
import { homeEnvironment } from "./environment";
import type { Device } from "../types/device";
it("家庭環境優先除濕機且斷線不沿用舊值", () => {
  const sensor = {
    id: "s",
    type: "sensor",
    available: true,
    stale: false,
    attributes: { temperature: 20, humidity: 60 },
  } as Device;
  const dh = {
    ...sensor,
    id: "d",
    type: "dehumidifier",
    attributes: { temperature: 24, humidity: 40 },
  } as Device;
  expect(homeEnvironment([sensor, dh])?.id).toBe("d");
  expect(
    homeEnvironment([sensor, { ...dh, available: false }]),
  ).toBeUndefined();
});
