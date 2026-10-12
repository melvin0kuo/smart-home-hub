import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
const env = readFileSync("../.env", "utf8");
if (!/^HUB_MODE=mock\s*$/m.test(env)) throw new Error("E2E 只允許 Mock 設定");
const password = env.match(/^HUB_ADMIN_PASSWORD=(.*)$/m)![1].trim();
test("登入、逐孔開關、情境與手機版", async ({ page }) => {
  const health = await page.request.get("/api/health");
  expect((await health.json()).mode).toBe("mock");
  await page.goto("/");
  await page.getByLabel("密碼").fill(password);
  await page.getByRole("button", { name: "登入平台" }).click();
  await expect(page.getByRole("heading", { name: "我的家庭" })).toBeVisible();
  await expect(page.locator("[data-device-id]")).toHaveCount(6);
  await expect(page.getByText("Mock Mode · 模擬測試環境")).toBeVisible();
  await page
    .getByRole("button", { name: "開啟書房智慧擴充插座詳細控制", exact: true })
    .click();
  const strip = page.locator('dialog [data-device-id="mock-p306"]');
  await expect(strip.getByRole("switch")).toHaveCount(3);
  await expect(strip.getByText("一般插座", { exact: true })).toHaveCount(3);
  const button = strip.getByRole("switch", { name: "插孔 1" });
  const before = await button.getAttribute("aria-checked");
  await button.click();
  await expect(button).toHaveAttribute(
    "aria-checked",
    before === "true" ? "false" : "true",
  );
  await expect(page.getByText("模擬操作已確認").first()).toBeVisible();
  await page.getByRole("button", { name: "返回裝置列表", exact: true }).click();
  const diffuser = page.locator('[data-device-id="mock-diffuser"]');
  await expect(diffuser.getByRole("switch")).toHaveCount(0);
  await page.getByRole("button", { name: "工作模式" }).click();
  await expect(page.getByText("工作模式已執行（模擬）")).toBeVisible();
  await page
    .getByRole("button", { name: "開啟工作桌檯燈詳細控制", exact: true })
    .click();
  const brightness = page.getByRole("slider", { name: "亮度" });
  await brightness.focus();
  await brightness.press("Home");
  await expect(brightness).toHaveValue("0");
  await expect(brightness).toBeEnabled();
  await page.getByRole("button", { name: "返回裝置列表", exact: true }).click();
  await page.getByRole("button", { name: "切換色彩模式" }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/mobile.png",
    fullPage: true,
    animations: "disabled",
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({
    path: "test-results/desktop.png",
    fullPage: true,
    animations: "disabled",
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "登出" }).click();
  await expect(page.getByRole("button", { name: "登入平台" })).toBeVisible();
});
