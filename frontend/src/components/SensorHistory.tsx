import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../services/api";
import type { Device } from "../types/device";
import type { HistoryPoint } from "../types/history";
import { chartSegments } from "./historyChart";

function Plot({
  points,
  hours,
  label,
  unit,
  color,
  bucket,
  rangeEnd,
}: {
  points: HistoryPoint[];
  hours: number;
  label: string;
  unit: string;
  color: string;
  bucket: number;
  rangeEnd: string;
}) {
  const values = points.flatMap((p) => (p.value === null ? [] : [p.value]));
  if (!values.length) return <p>{label}：此範圍尚無量測資料。</p>;
  const end = Date.parse(rangeEnd),
    start = end - hours * 3600000;
  const low = Math.min(...values),
    high = Math.max(...values),
    padding = Math.max((high - low) * 0.15, 0.5);
  const x = (at: string) =>
    45 + ((Date.parse(at) - start) / (end - start)) * 550;
  const y = (value: number) =>
    150 - ((value - low + padding) / (high - low + 2 * padding)) * 125;
  const format = (stamp: number) =>
    new Date(stamp).toLocaleString("zh-TW", {
      month: "numeric",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  const segments = chartSegments(points, Math.max(1800, bucket * 3));
  return (
    <figure className="sensor-history-plot">
      <figcaption>
        {label}{" "}
        <span>
          {low.toFixed(1)}–{high.toFixed(1)} {unit}（圖中平均值範圍）
        </span>
      </figcaption>
      <svg
        viewBox="0 0 620 190"
        role="img"
        aria-label={`${label}歷史曲線，單位 ${unit}`}
      >
        {[low, (low + high) / 2, high]
          .filter((v, i, a) => a.indexOf(v) === i)
          .map((value) => (
            <g key={value}>
              <line
                x1="45"
                x2="595"
                y1={y(value)}
                y2={y(value)}
                stroke="currentColor"
                opacity=".12"
              />
              <text
                x="38"
                y={y(value) + 4}
                textAnchor="end"
                fill="currentColor"
                fontSize="11"
              >
                {value.toFixed(1)}
              </text>
            </g>
          ))}
        {segments.map((segment, index) => (
          <g key={index}>
            <polyline
              points={segment.map((p) => `${x(p.at)},${y(p.value)}`).join(" ")}
              fill="none"
              stroke={color}
              strokeWidth="2.5"
            />
            {segment.length === 1 && (
              <circle
                cx={x(segment[0].at)}
                cy={y(segment[0].value)}
                r="3"
                fill={color}
              />
            )}
          </g>
        ))}
        <text x="45" y="180" fill="currentColor" fontSize="11">
          {format(start)}
        </text>
        <text
          x="595"
          y="180"
          fill="currentColor"
          fontSize="11"
          textAnchor="end"
        >
          {format(end)}
        </text>
      </svg>
    </figure>
  );
}

export function SensorHistory({ device }: { device: Device }) {
  const [hours, setHours] = useState(24);
  const query = useQuery({
    queryKey: ["sensor-history", device.id, hours],
    queryFn: () => api.sensorHistory(device.id, hours),
    refetchInterval: 60000,
  });
  return (
    <section className="sensor-history" aria-label="環境歷史紀錄">
      <header>
        <h3>歷史紀錄</h3>
        <div className="history-ranges" aria-label="歷史範圍">
          {[
            [24, "24 小時"],
            [168, "7 天"],
            [720, "30 天"],
          ].map(([value, label]) => (
            <button
              key={value}
              aria-pressed={hours === value}
              onClick={() => setHours(Number(value))}
            >
              {label}
            </button>
          ))}
        </div>
      </header>
      <p>
        保存於平台本機 SQLite ·{" "}
        {device.source === "mock" ? "模擬紀錄" : "真實量測紀錄"} · 不自動刪除
      </p>
      {query.isPending ? (
        <p role="status">正在載入歷史資料…</p>
      ) : query.isError ? (
        <p className="error" role="alert">
          無法讀取歷史資料。
          <button onClick={() => void query.refetch()}>重試</button>
        </p>
      ) : (
        <>
          {query.data.sync_failed && (
            <p role="status">HA 歷史同步暫時失敗，以下仍可查看已保存資料。</p>
          )}
          {(
            [
              ["temperature", "溫度", "°C", "#d9824e"],
              ["humidity", "相對濕度", "%", "#399bb4"],
            ] as const
          )
            .filter(([metric]) =>
              device.capabilities.some((c) => c.name === `${metric}_sensor`),
            )
            .map(([metric, label, unit, color]) => (
              <div key={metric}>
                <Plot
                  points={query.data.series[metric] || []}
                  hours={hours}
                  label={label}
                  unit={unit}
                  color={color}
                  bucket={query.data.bucket_seconds}
                  rangeEnd={query.data.range_end}
                />
                {query.data.summary[metric]?.samples ? (
                  <p>
                    原始紀錄最低{" "}
                    {query.data.summary[metric]?.minimum?.toFixed(1)}
                    {unit} ／ 最高{" "}
                    {query.data.summary[metric]?.maximum?.toFixed(1)}
                    {unit} · {query.data.summary[metric]?.samples} 筆
                  </p>
                ) : null}
              </div>
            ))}
          <p>
            圖表依時間區間平均；斷線或相隔過久的紀錄不連線。首次補入 HA
            歷史需要一些時間，米家舊紀錄尚未匯入。
          </p>
        </>
      )}
    </section>
  );
}
