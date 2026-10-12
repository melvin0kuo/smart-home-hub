import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import {
  DeviceOnboarding,
  OnboardingCatalog,
  OnboardingGuide,
} from "./DeviceOnboarding";
import { searchIntegrations } from "../services/onboarding";
import type { IntegrationOption } from "../types/onboarding";

const options: IntegrationOption[] = [
  {
    domain: "tplink",
    name: "TP-Link",
    keywords: "Tapo Kasa",
    category: "品牌",
    available: true,
    requirements: "相容設備",
    instructions: "完成官方設定",
    documentation_url: "https://www.home-assistant.io/integrations/tplink/",
    setup_url:
      "https://ha.example/config/integrations/dashboard/add?domain=tplink",
  },
  {
    domain: "zha",
    name: "Zigbee",
    keywords: "ZHA",
    category: "協定",
    available: false,
    requirements: "Zigbee 協調器",
    instructions: "先安裝",
    documentation_url: "https://www.home-assistant.io/integrations/zha/",
    setup_url: null,
  },
];

it("搜尋品牌別名與協定，大小寫及空白不影響結果", () => {
  expect(searchIntegrations(options, " TAPO ", "all")[0].domain).toBe("tplink");
  expect(
    searchIntegrations(options, "", "protocol").map((x) => x.domain),
  ).toEqual(["zha"]);
  expect(searchIntegrations(options, "unknown", "all")).toEqual([]);
  expect(
    searchIntegrations(
      [{ ...options[1], available: true }, options[0]],
      "",
      "all",
    )[0].domain,
  ).toBe("zha");
});

it("目錄標示可設定與未提供，而不宣稱型號已驗證", () => {
  const html = renderToStaticMarkup(
    <OnboardingCatalog options={options} onSelect={() => {}} />,
  );
  expect(html).toContain("可進行設定");
  expect(html).toContain("此 HA 尚未提供");
});

it("探索頁提供共用配對完成入口，不必另找目錄指引", () => {
  const html = renderToStaticMarkup(<DeviceOnboarding onPaired={() => {}} />);
  expect(html).toContain("配對完成，讀取設備");
});

it("配對在 HA 獨立分頁進行，Mock 與缺少整合不提供真實連結", () => {
  const html = renderToStaticMarkup(
    <OnboardingGuide option={options[0]} mock={false} onReturn={() => {}} />,
  );
  expect(html).toContain('target="_blank"');
  expect(html).toContain('rel="noopener noreferrer"');
  expect(html).toContain("配對完成，讀取設備");
  expect(html).toContain("完成官方設定");
  const mock = renderToStaticMarkup(
    <OnboardingGuide option={options[0]} mock onReturn={() => {}} />,
  );
  expect(mock).not.toContain('href="https://ha.example');
  expect(mock).toContain("模擬模式");
  const missing = renderToStaticMarkup(
    <OnboardingGuide option={options[1]} mock={false} onReturn={() => {}} />,
  );
  expect(missing).not.toContain("在 HA 開始設定");
  expect(missing).toContain("Zigbee 協調器");
});
