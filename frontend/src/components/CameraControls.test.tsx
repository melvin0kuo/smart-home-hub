import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { CameraControls } from "./CameraControls";
import type { Device } from "../types/device";

it("未驗證不顯示控制；隱私、離線與唯讀均禁止方向操作", () => {
  const device = {
    id: "cam",
    available: true,
    capabilities: [],
    attributes: {},
  } as unknown as Device;
  expect(
    renderToStaticMarkup(<CameraControls device={device} readOnly={false} />),
  ).toBe("");
  device.capabilities = [
    {
      name: "camera_ptz",
      writable: true,
      readable: true,
      target: "ptz",
      verification_status: "verified",
    },
  ];
  device.attributes = { privacy_available: true, privacy_enabled: false };
  expect(
    renderToStaticMarkup(<CameraControls device={device} readOnly={false} />),
  ).not.toContain("disabled");
  for (const state of [
    { privacy_enabled: true },
    { privacy_available: false },
  ]) {
    const html = renderToStaticMarkup(
      <CameraControls
        device={{ ...device, attributes: { ...device.attributes, ...state } }}
        readOnly={false}
      />,
    );
    expect((html.match(/disabled/g) ?? []).length).toBe(
      state.privacy_enabled === true ? 5 : 4,
    );
  }
  expect(
    (
      renderToStaticMarkup(
        <CameraControls device={device} readOnly={true} />,
      ).match(/disabled/g) ?? []
    ).length,
  ).toBe(5);
});
