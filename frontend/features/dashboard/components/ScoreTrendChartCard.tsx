"use client";

import {
  Area,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

import { InfoCard } from "../../app-shell/components/InfoCard";
import { SectionTitle } from "../../app-shell/components/SectionTitle";
import type { DashboardScoreTrendPoint } from "../analytics-utils";

type ScoreTrendChartCardProps = {
  points: DashboardScoreTrendPoint[];
};

export function ScoreTrendChartCard({ points }: ScoreTrendChartCardProps) {
  const latestPoint = points.find((point) => point.isLatest) ?? null;

  return (
    <InfoCard>
      <SectionTitle
        eyebrow="Trend"
        title="Score trend"
        description="Recent session scores plotted over time so you can spot direction quickly."
      />

      {points.length < 2 ? (
        <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4 text-sm leading-7 text-muted-gray">
          Complete more sessions to unlock a performance trend line.
        </div>
      ) : (
        <div className="mt-6 h-[320px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={points} margin={{ top: 12, right: 18, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="scoreTrendFill" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="#ff7a00" stopOpacity={0.26} />
                  <stop offset="100%" stopColor="#ff7a00" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
              <XAxis
                dataKey="label"
                tick={{ fill: "rgba(255,255,255,0.55)", fontSize: 12 }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fill: "rgba(255,255,255,0.55)", fontSize: 12 }}
                tickLine={false}
                axisLine={false}
                width={40}
              />
              <Tooltip
                cursor={{ stroke: "rgba(255,255,255,0.18)", strokeWidth: 1 }}
                contentStyle={{
                  background: "rgba(10, 12, 16, 0.96)",
                  border: "1px solid rgba(255,255,255,0.12)",
                  borderRadius: "18px",
                  color: "white"
                }}
                formatter={(value: number, name: string) => [
                  `${value.toFixed(0)}%`,
                  name === "score" ? "Session score" : "Moving average"
                ]}
                labelFormatter={(label) => {
                  const point = points.find((item) => item.label === label);
                  return point?.fullLabel ?? label;
                }}
              />
              <Area
                type="monotone"
                dataKey="score"
                fill="url(#scoreTrendFill)"
                stroke="transparent"
              />
              <Line
                type="monotone"
                dataKey="score"
                stroke="#ff7a00"
                strokeWidth={3}
                dot={{ fill: "#ff7a00", strokeWidth: 0, r: 4 }}
                activeDot={{ r: 6, stroke: "#0a0c10", strokeWidth: 2 }}
              />
              <Line
                type="monotone"
                dataKey="movingAverage"
                stroke="rgba(255,255,255,0.65)"
                strokeDasharray="6 6"
                strokeWidth={2}
                dot={false}
                connectNulls
              />
              {latestPoint ? (
                <ReferenceDot
                  x={latestPoint.label}
                  y={latestPoint.score}
                  r={7}
                  fill="#fff"
                  stroke="#ff7a00"
                  strokeWidth={3}
                />
              ) : null}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </InfoCard>
  );
}
