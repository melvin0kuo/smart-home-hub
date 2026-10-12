import { describe, it, expect } from "vitest";
import { canControl, type Device } from "./device";
describe("設備能力", () => {
  const base = {
    available: true,
    stale: false,
    capabilities: [
      {
        name: "switch",
        target: "outlet-1",
        writable: true,
        verification_status: "mock",
      },
    ],
  } as Device;
  it("僅對對應子單元提供開關", () => {
    expect(canControl(base, "switch", "outlet-1")).toBe(true);
    expect(canControl(base, "switch", "outlet-2")).toBe(false);
  });
  it("離線、過期、未驗證不可控制", () => {
    expect(
      canControl({ ...base, available: false }, "switch", "outlet-1"),
    ).toBe(false);
    expect(canControl({ ...base, stale: true }, "switch", "outlet-1")).toBe(
      false,
    );
    expect(
      canControl(
        {
          ...base,
          capabilities: [
            { ...base.capabilities[0], verification_status: "pending" },
          ],
        },
        "switch",
        "outlet-1",
      ),
    ).toBe(false);
  });
});
