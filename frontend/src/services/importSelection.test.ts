import { expect, it } from "vitest";
import { canEnableImportedControl, filterCandidates } from "./importSelection";
import type { ImportCandidate } from "../types/imports";

const candidate = {
  entity_id: "light.demo",
  name: "閱讀燈",
  type: "light",
  supported: true,
  already_imported: false,
  available: true,
  can_test: true,
  tested_actions: ["turn_on", "turn_off"],
} as ImportCandidate;

it("已匯入或待支援候選不混入可加入列表，搜尋可用名稱與實體", () => {
  const list = [
    candidate,
    { ...candidate, already_imported: true },
    { ...candidate, supported: false },
  ];
  expect(filterCandidates(list, "available", "閱讀")).toEqual([candidate]);
  expect(filterCandidates(list, "all", "light.demo")).toHaveLength(3);
  expect(filterCandidates(list, "all", "不存在")).toHaveLength(0);
});

it("保護、離線、未完成雙向測試不能開放控制", () => {
  expect(canEnableImportedControl(candidate, false)).toBe(true);
  expect(canEnableImportedControl(candidate, true)).toBe(false);
  expect(
    canEnableImportedControl({ ...candidate, available: false }, false),
  ).toBe(false);
  expect(
    canEnableImportedControl(
      { ...candidate, tested_actions: ["turn_on"] },
      false,
    ),
  ).toBe(false);
});
