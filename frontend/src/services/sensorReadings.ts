import type { Device } from "../types/device";
export function sensorReadings(device: Device) {
  const definitions = [
    ["temperature_sensor", "temperature", "溫度", "°C"],
    ["humidity_sensor", "humidity", "相對濕度", "%"],
    ["battery_sensor", "battery", "電量", "%"],
    ["power_monitoring", "power_w", "即時功率", "W"],
  ] as const;
  return definitions
    .filter(([cap]) => device.capabilities.some((c) => c.name === cap))
    .map(([cap, field, label, unit]) => ({
      cap,
      label,
      unit,
      value: device.attributes[field] ?? "—",
    }));
}
