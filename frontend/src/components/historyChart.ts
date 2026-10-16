import type { HistoryPoint } from "../types/history";

export function chartSegments(points: HistoryPoint[], gapSeconds: number) {
  const segments: { at: string; value: number }[][] = [];
  let current: { at: string; value: number }[] = [];
  for (const point of points) {
    const previous = current.at(-1);
    if (
      point.value === null ||
      (previous &&
        Date.parse(point.at) - Date.parse(previous.at) > gapSeconds * 1000)
    ) {
      if (current.length) segments.push(current);
      current = [];
    }
    if (point.value !== null)
      current.push({ at: point.at, value: point.value });
  }
  if (current.length) segments.push(current);
  return segments;
}
