import type { Device } from "../types/device";
export function homeEnvironment(devices: Device[]): Device | undefined {
  const source =
    devices.find((d) => d.type === "dehumidifier") ??
    devices.find((d) => d.type === "sensor");
  return source?.available && !source.stale ? source : undefined;
}
