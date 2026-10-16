export type HistoryPoint = { at: string; value: number | null };
export type SensorHistoryData = {
  range_end: string;
  hours: number;
  mode: string;
  series: Partial<Record<"temperature" | "humidity", HistoryPoint[]>>;
  summary: Partial<
    Record<
      "temperature" | "humidity",
      { minimum: number | null; maximum: number | null; samples: number }
    >
  >;
  bucket_seconds: number;
  sync_failed: boolean;
};
