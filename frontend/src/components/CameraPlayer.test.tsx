import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { CameraPlayer } from "./CameraPlayer";
import type { Device } from "../types/device";

it("隱私模式開啟時不載入影片，禁止播放", () => {
  const device = {
    id: "camera",
    name: "C260",
    available: true,
    capabilities: [
      {
        name: "camera_stream",
        readable: true,
        verification_status: "verified",
      },
    ],
    attributes: { privacy_enabled: true },
  } as Device;
  const html = renderToStaticMarkup(<CameraPlayer device={device} />);
  expect(html).toContain("隱私模式已開啟，鏡頭遮蔽");
  expect(html).toContain("disabled");
  expect(html).not.toContain("<video");
  const available = renderToStaticMarkup(
    <CameraPlayer
      device={{ ...device, attributes: { privacy_enabled: false } }}
    />,
  );
  expect(available).not.toContain("disabled");
  expect(available).not.toContain("<video");
});
