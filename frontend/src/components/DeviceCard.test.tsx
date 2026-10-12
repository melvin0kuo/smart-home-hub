import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { DeviceCard } from "./DeviceCard";
import type { Device } from "../types/device";

it("燈具沒有回報亮度或色溫時，不把滑桿最低值當成目前讀值", () => {
  const device = {
    id: "lamp",
    name: "米家檯燈",
    type: "light",
    manufacturer: "Xiaomi",
    model: "yeelink.light.lamp4",
    room: "書房",
    online: true,
    available: true,
    state: "off",
    source: "home_assistant",
    capabilities: [
      {
        name: "brightness",
        target: "main",
        writable: true,
        verification_status: "verified",
        minimum: 1,
        maximum: 100,
        unit: "%",
      },
      {
        name: "color_temperature",
        target: "main",
        writable: true,
        verification_status: "verified",
        minimum: 2600,
        maximum: 5000,
        unit: "K",
      },
    ],
    attributes: {},
  } as Device;
  const render = (value: Device) =>
    renderToStaticMarkup(
      <DeviceCard device={value} readOnly={false} onAction={async () => {}} />,
    );
  const missing = render(device);
  expect(missing.match(/尚未回報/g)).toHaveLength(2);
  expect(missing.match(/disabled=""/g)).toHaveLength(2);
  const reported = render({
    ...device,
    state: "on",
    attributes: { brightness: 63, color_temperature: 5000 },
  });
  expect(reported).not.toContain("尚未回報");
  expect(reported).toContain("63%");
  expect(reported).toContain("5000K");
  expect(reported).not.toContain("disabled");
});

it("總覽攝影機僅提供入口，不掛載影像或旋轉控制", () => {
  const device = {
    id: "camera",
    name: "Tapo C260",
    type: "camera",
    room: "客廳",
    manufacturer: "TP-Link",
    model: "C260",
    online: true,
    available: true,
    state: "idle",
    source: "home_assistant",
    attributes: { privacy_available: true, privacy_enabled: false },
    capabilities: [
      { name: "camera_stream", verification_status: "verified" },
      { name: "camera_ptz", writable: true, verification_status: "verified" },
      {
        name: "camera_privacy",
        target: "privacy",
        writable: true,
        verification_status: "verified",
      },
    ],
  } as Device;
  const html = renderToStaticMarkup(
    <DeviceCard
      device={device}
      readOnly={false}
      onAction={async () => {}}
      compactCamera
      onOpenCamera={() => {}}
    />,
  );
  expect(html).toContain("開啟攝影機");
  expect(html).not.toContain("播放即時影像");
  expect(html).not.toContain("停止旋轉");
  expect(html).not.toContain('role="switch"');
});

it("除濕機顯示實際環境與滿水警示，未驗證控制不顯示開關", () => {
  const device = {
    id: "dehumidifier",
    name: "伊萊克斯除濕機",
    type: "dehumidifier",
    manufacturer: "Electrolux",
    model: "EDH14TRBD2",
    room: "客廳",
    online: true,
    available: true,
    state: "on",
    source: "home_assistant",
    stale: false,
    verification_status: "verified",
    state_confidence: "reported",
    last_updated: null,
    capabilities: [],
    attributes: { temperature: 24, humidity: 44, water_tank_full: true },
  } as Device;
  const html = renderToStaticMarkup(
    <DeviceCard device={device} readOnly={false} onAction={async () => {}} />,
  );
  expect(html).toContain("水箱已滿");
  expect(html).toContain("相對濕度");
  expect(html).not.toContain('role="switch"');
});

it("除濕機僅在完整手動模式開放目標濕度", () => {
  const device = {
    id: "dh",
    name: "除濕機",
    type: "dehumidifier",
    manufacturer: "Electrolux",
    model: "EDH14TRBD2",
    room: "家",
    online: true,
    available: true,
    state: "on",
    source: "home_assistant",
    stale: false,
    verification_status: "verified",
    state_confidence: "reported",
    last_updated: null,
    capabilities: [
      {
        name: "target_humidity",
        target: "humidity_target",
        readable: true,
        writable: true,
        verification_status: "verified",
        minimum: 35,
        maximum: 85,
        step: 5,
      },
    ],
    attributes: {
      mode: "Complete",
      operative_mode: "Automatic",
      target_humidity: 50,
    },
  } as Device;
  const render = (d: Device) =>
    renderToStaticMarkup(
      <DeviceCard device={d} readOnly={false} onAction={async () => {}} />,
    );
  expect(render(device)).toContain("雙效＋手動模式");
  expect(render(device)).toMatch(/<select[^>]*disabled/);
  expect(
    render({
      ...device,
      attributes: { ...device.attributes, operative_mode: "Manual" },
    }),
  ).not.toMatch(/<select[^>]*disabled/);
});

it("風速提供高中低並在智慧模式停用手動調整", () => {
  const device = {
    id: "dh",
    name: "除濕機",
    type: "dehumidifier",
    manufacturer: "Electrolux",
    model: "EDH14TRBD2",
    room: "家",
    available: true,
    online: true,
    state: "on",
    source: "home_assistant",
    stale: false,
    verification_status: "verified",
    state_confidence: "reported",
    last_updated: null,
    attributes: {
      operative_mode: "Automatic",
      mode: "Complete",
      fan_speed: "Auto",
    },
    capabilities: [
      {
        name: "fan_speed",
        target: "fan_speed",
        writable: true,
        readable: true,
        verification_status: "verified",
        options: ["Low", "Middle", "High"],
      },
    ],
  } as Device;
  const html = renderToStaticMarkup(
    <DeviceCard device={device} readOnly={false} onAction={async () => {}} />,
  );
  expect(html).toContain('aria-label="風速"');
  expect(html).toContain("中速");
  expect(html).toMatch(/<select[^>]*disabled/);
});

it("除濕機提供獨立上下擺風開關，未知狀態禁止操作", () => {
  const device = {
    id: "dh",
    name: "除濕機",
    type: "dehumidifier",
    manufacturer: "Electrolux",
    model: "EDH14TRBD2",
    room: "家",
    available: true,
    online: true,
    state: "on",
    source: "home_assistant",
    stale: false,
    verification_status: "verified",
    state_confidence: "reported",
    last_updated: null,
    attributes: { vertical_swing: true },
    capabilities: [
      {
        name: "switch",
        target: "swing",
        writable: true,
        readable: true,
        verification_status: "verified",
      },
    ],
  } as Device;
  const render = (d: Device) =>
    renderToStaticMarkup(
      <DeviceCard device={d} readOnly={false} onAction={async () => {}} />,
    );
  expect(render(device)).toContain('aria-label="上下自動擺風"');
  expect(render(device)).toContain('aria-checked="true"');
  expect(render({ ...device, attributes: { vertical_swing: null } })).toMatch(
    /role="switch"[^>]*disabled/,
  );
});

it("藍牙香氛機顯示兩個已驗證控制，離線時保留狀態說明並停用", () => {
  const device = {
    id: "ble",
    name: "米家智慧香氛機",
    manufacturer: "Xiaomi",
    model: "xiaomi.diffuser.xw2iv",
    type: "diffuser",
    room: "居家",
    source: "bluetooth",
    online: true,
    available: true,
    state: "on",
    capabilities: ["main", "light"].map((target) => ({
      name: "switch",
      target,
      writable: true,
      verification_status: "verified",
    })),
    attributes: {
      light_on: false,
      battery: 100,
      diffusion_seconds: 4,
      diffusion_interval: 20,
    },
  } as Device;
  const html = (d: Device) =>
    renderToStaticMarkup(
      <DeviceCard device={d} readOnly={false} onAction={async () => {}} />,
    );
  expect(html(device)).toContain("藍牙直連");
  expect(html(device)).toContain('aria-label="香氛燈光"');
  expect(html(device)).toContain("電量 100%");
  expect(html(device)).not.toContain("保留紀錄");
  expect(
    html({
      ...device,
      available: false,
      online: false,
      stale: true,
      attributes: {},
    }),
  ).toContain('disabled=""');
});
