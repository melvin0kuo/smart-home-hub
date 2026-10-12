export interface Capability {
  name: string;
  target: string;
  readable: boolean;
  writable: boolean;
  verification_status: "mock" | "verified" | "pending" | "unsupported";
  step?: number;
  options?: string[];
  minimum?: number;
  maximum?: number;
  unit?: string;
  label?: string | null;
  control_note?: string | null;
}
export interface Device {
  id: string;
  name: string;
  manufacturer: string;
  model: string;
  type: string;
  room: string;
  online: boolean | null;
  available: boolean;
  state: string;
  capabilities: Capability[];
  attributes: {
    outlets?: {
      id: string;
      name: string;
      state: string;
      control_note?: string | null;
    }[];
    brightness?: number | null;
    color?: number | null;
    color_temperature?: number;
    temperature?: number;
    humidity?: number;
    battery?: number | null;
    light_on?: boolean | null;
    diffusion_seconds?: number | null;
    diffusion_interval?: number | null;
    water_tank_full?: boolean | null;
    target_humidity?: number | null;
    vertical_swing?: boolean | null;
    fan_speed?: string | null;
    mode?: string | null;
    operative_mode?: string | null;
    power_w?: number;
    note?: string;
    privacy_available?: boolean;
    privacy_enabled?: boolean | null;
  };
  source: "mock" | "home_assistant" | "bluetooth";
  stale: boolean;
  verification_status: string;
  state_confidence: string;
  last_updated: string | null;
  integration_note?: string | null;
}
export interface Session {
  role: "admin" | "viewer";
  csrf_token: string;
  mode: "mock" | "real";
}
export interface Operation {
  operation_id: string;
  occurred_at: string;
  device_id: string;
  action: string;
  target: string;
  status: string;
  mode: string;
}
export interface Scene {
  id: string;
  name: string;
  source: string;
}
export interface Action {
  action:
    | "turn_on"
    | "turn_off"
    | "set_brightness"
    | "set_color_temperature"
    | "enable_privacy"
    | "disable_privacy"
    | "set_target_humidity"
    | "set_mode"
    | "set_operative_mode"
    | "set_fan_speed"
    | "set_diffusion_duration"
    | "set_diffusion_interval"
    | "set_color";
  target?: string;
  parameters?: { value: number | string };
}
export function canControl(
  device: Device,
  name: string,
  target = "main",
): boolean {
  return (
    device.available &&
    !device.stale &&
    device.capabilities.some(
      (c) =>
        c.name === name &&
        c.target === target &&
        c.writable &&
        ["mock", "verified"].includes(c.verification_status),
    )
  );
}
