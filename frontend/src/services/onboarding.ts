import type { IntegrationOption } from "../types/onboarding";

export function searchIntegrations(
  options: IntegrationOption[],
  query: string,
  category: "all" | "protocol",
) {
  const text = query.trim().toLocaleLowerCase();
  return options
    .filter(
      (option) =>
        (category !== "protocol" || option.category === "協定") &&
        `${option.name} ${option.domain} ${option.keywords}`
          .toLocaleLowerCase()
          .includes(text),
    )
    .sort(
      (a, b) =>
        Number(b.available) - Number(a.available) ||
        Number(b.category === "協定") - Number(a.category === "協定") ||
        Number(b.category === "品牌") - Number(a.category === "品牌") ||
        a.name.localeCompare(b.name, "zh-TW"),
    );
}
