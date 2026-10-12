import type { ImportCandidate } from "../types/imports";
export type ImportFilter = "available" | "imported" | "unsupported" | "all";
export function filterCandidates(
  candidates: ImportCandidate[],
  filter: ImportFilter,
  search: string,
) {
  const term = search.trim().toLowerCase();
  return candidates.filter(
    (c) =>
      (filter === "all" ||
        (filter === "available" && c.supported && !c.already_imported) ||
        (filter === "imported" && c.already_imported) ||
        (filter === "unsupported" && !c.supported && !c.already_imported)) &&
      `${c.name} ${c.entity_id}`.toLowerCase().includes(term),
  );
}
export function canEnableImportedControl(
  candidate: ImportCandidate,
  protectedDevice: boolean,
) {
  return (
    !protectedDevice &&
    candidate.available &&
    candidate.can_test &&
    candidate.tested_actions.includes("turn_on") &&
    candidate.tested_actions.includes("turn_off")
  );
}
