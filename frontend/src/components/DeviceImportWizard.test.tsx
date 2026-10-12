import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { ImportCandidateList } from "./DeviceImportWizard";
import type { ImportCandidate } from "../types/imports";

it("候選清楚區分已加入、待支援及離線，無法選取不支援的實體", () => {
  const rows = [
    {
      entity_id: "switch.router",
      name: "路由器",
      type: "switch",
      already_imported: true,
      supported: true,
      available: true,
    },
    {
      entity_id: "remote.demo",
      name: "遙控器",
      type: "remote",
      already_imported: false,
      supported: false,
      available: true,
    },
    {
      entity_id: "light.demo",
      name: "燈",
      type: "light",
      already_imported: false,
      supported: true,
      available: false,
    },
  ] as ImportCandidate[];
  const html = renderToStaticMarkup(
    <ImportCandidateList candidates={rows} selected={[]} onToggle={() => {}} />,
  );
  expect(html.match(/disabled=""/g)).toHaveLength(2);
  expect(html).toContain("已加入");
  expect(html).toContain("待支援");
  expect(html).toContain("離線 · 僅能唯讀匯入");
  expect(html).toContain("switch.router");
});
