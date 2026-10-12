import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { DiffuserSettings } from "./DiffuserSettings";
import type { Device } from "../types/device";

it("已驗證數值設定依範圍顯示，缺少讀值時不可操作", () => {
  const device = {
    available: true,
    stale: false,
    attributes: { diffusion_seconds: 4, color: 0xfaead3 },
    capabilities: [
      {
        name: "diffusion_duration",
        target: "main",
        writable: true,
        verification_status: "verified",
        minimum: 2,
        maximum: 6,
        step: 1,
        unit: "秒",
      },
      {
        name: "color",
        target: "light",
        writable: true,
        verification_status: "verified",
      },
      {
        name: "brightness",
        target: "light",
        writable: true,
        verification_status: "pending",
      },
    ],
  } as Device;
  const render = (d: Device) =>
    renderToStaticMarkup(
      <DiffuserSettings
        device={d}
        disabled={false}
        onAction={async () => {}}
      />,
    );
  const html = render(device);
  expect(html).toContain('value="4" selected');
  expect(html).toContain("#FAEAD3");
  expect(html).not.toContain("氛圍燈亮度");
  expect(html).toContain("定時排程尚未接入");
  expect(render({ ...device, attributes: {} })).toContain('disabled=""');
});
