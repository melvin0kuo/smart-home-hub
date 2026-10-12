import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { DeviceShortcut } from "./DeviceShortcut";
import type { Device } from "../types/device";

const base = {
  id: "test",
  name: "香氛機",
  type: "diffuser",
  manufacturer: "Xiaomi",
  room: "居家",
  available: true,
  online: true,
  state: "on",
  capabilities: [
    {
      name: "switch",
      target: "main",
      writable: true,
      verification_status: "verified",
    },
  ],
  attributes: { battery: 85 },
  source: "bluetooth",
} as Device;
const render = (device: Device) =>
  renderToStaticMarkup(
    <DeviceShortcut
      device={device}
      readOnly={false}
      onOpen={() => {}}
      onAction={async () => {}}
    />,
  );

it("重要告警在捷徑上仍可見", () => {
  expect(
    render({
      ...base,
      type: "dehumidifier",
      attributes: { water_tank_full: true },
    }),
  ).toContain("水箱已滿");
});
it("捷徑不掛載進階設定，提供清楚的詳情入口", () => {
  const html = render(base);
  expect(html).toContain("開啟香氛機詳細控制");
  expect(html).toContain('role="switch"');
  expect(html).not.toContain('type="range"');
  expect(html).not.toContain("<select");
});
it("離線與未驗證能力不能使用快捷開關", () => {
  expect(render({ ...base, available: false })).toContain('disabled=""');
  expect(render({ ...base, capabilities: [] })).not.toContain('role="switch"');
});
it("延長線不提供總開關或被鎖定插孔控制", () => {
  const html = render({
    ...base,
    type: "power_strip",
    capabilities: [],
    attributes: {
      outlets: [
        { id: "outlet2", name: "路由器", state: "on", control_note: "已鎖定" },
      ],
    },
  });
  expect(html).not.toContain('role="switch"');
});
