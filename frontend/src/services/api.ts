import type {
  Action,
  Device,
  Operation,
  Scene,
  Session,
} from "../types/device";
import type { ImportDiscovery, ImportItem } from "../types/imports";
import type { OnboardingData } from "../types/onboarding";
let csrf = "";
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
async function request<T>(path: string, body?: unknown): Promise<T> {
  const controller = new AbortController(),
    timeout = window.setTimeout(() => controller.abort(), 45000);
  try {
    const response = await fetch(`/api${path}`, {
      method: body === undefined ? "GET" : "POST",
      credentials: "same-origin",
      signal: controller.signal,
      headers:
        body === undefined
          ? {}
          : { "Content-Type": "application/json", "X-CSRF-Token": csrf },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const data = await response.json();
    if (!response.ok)
      throw new ApiError(
        response.status,
        data.error?.message || "請求失敗，請稍後再試。",
      );
    return data as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new Error("無法取得服務回應，請確認後端已啟動。", { cause: error });
  } finally {
    window.clearTimeout(timeout);
  }
}
async function session(path: string, body?: unknown) {
  const result = await request<Session>(path, body);
  csrf = result.csrf_token;
  return result;
}
export const api = {
  onboarding: () =>
    request<OnboardingData>("/integrations/home-assistant/onboarding"),
  importCandidates: () =>
    request<ImportDiscovery>("/integrations/home-assistant/candidates"),
  testImportSwitch: (entity_id: string, action: "turn_on" | "turn_off") =>
    request<{
      status: string;
      state: string;
      tested_actions: string[];
      mode: string;
    }>("/integrations/home-assistant/test", {
      entity_id,
      action,
      confirmed_safe: true,
    }),
  importDevices: (devices: ImportItem[]) =>
    request<{ status: string; devices: Device[]; mode: string }>(
      "/integrations/home-assistant/import",
      { devices },
    ),
  cameraPtz: (
    id: string,
    direction: "left" | "right" | "up" | "down" | "stop",
  ) =>
    request<{ status: string; message: string }>(
      `/cameras/${encodeURIComponent(id)}/ptz`,
      { direction },
    ),
  infrared: () =>
    request<
      {
        id: string;
        name: string;
        gateway: string;
        note: string;
        supported: boolean;
        commands: { id: string; label: string }[];
      }[]
    >("/infrared"),
  infraredCommand: (id: string, command: string) =>
    request<{ status: string; message: string }>(
      `/infrared/${encodeURIComponent(id)}/commands/${encodeURIComponent(command)}`,
      {},
    ),
  me: () => session("/auth/me"),
  login: (username: string, password: string) =>
    session("/auth/login", { username, password }),
  logout: async () => {
    await request("/auth/logout", {});
    csrf = "";
  },
  devices: () => request<Device[]>("/devices"),
  history: () => request<Operation[]>("/history?limit=12"),
  scenes: () => request<Scene[]>("/scenes"),
  action: (id: string, action: Action) =>
    request<{ status: string }>(
      `/devices/${encodeURIComponent(id)}/actions`,
      action,
    ),
  scene: (id: string) =>
    request<{ status: string }>(
      `/scenes/${encodeURIComponent(id)}/execute`,
      {},
    ),
};
