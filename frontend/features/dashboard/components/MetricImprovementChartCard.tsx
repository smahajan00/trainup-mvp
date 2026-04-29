"use client";

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { InfoCard } from "../../app-shell/components/InfoCard";
import { SectionTitle } from "../../app-shell/components/SectionTitle";
import type { DashboardMetricImprovementPoint } from "../analytics-utils";

type MetricImprovementChartCardProps = {
  points: DashboardMetricImprovementPoint[];
};

export function MetricImprovementChartCard({
  points
}: MetricImprovementChartCardProps) {
  const hasTrendData = points.some((point) => point.hasTrend);

  return (
    <InfoCard>
      <SectionTitle
        eyebrow="Metrics"
        title="Metric Momentum"
        description="Track which movement metrics are climbing and which ones still need more clean reps."
      />

      {!points.length ? (
        <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4 text-sm leading-7 text-muted-gray">
          Log more sessions to compare metric changes.
        </div>
      ) : hasTrendData ? (
        <div className="mt-6 h-[320px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={points}
              layout="vertical"
              margin={{ top: 8, right: 18, left: 18, bottom: 8 }}
            >
              <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
              <XAxis
                type="number"
                tick={{ fill: "rgba(255,255,255,0.55)", fontSize: 12 }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                dataKey="shortLabel"
                type="category"
                width={110}
                tick={{ fill: "rgba(255,255,255,0.75)", fontSize: 12 }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                cursor={{ fill: "rgba(255,255,255,0.04)" }}
                contentStyle={{
                  background: "rgba(10, 12, 16, 0.96)",
                  border: "1px solid rgba(255,255,255,0.12)",
                  borderRadius: "18px",
                  color: "white"
                }}
                formatter={(value: number, name: string, context) => {
                  if (name === "change") {
                    return [`${value.toFixed(1)}%`, "Change vs first saved value"];
                  }

                  const point = context.payload as DashboardMetricImprovementPoint;
                  return [`${point.average.toFixed(2)} ${point.unit}`, "Recent average"];
                }}
                labelFormatter={(label) => String(label)}
              />
              <Bar dataKey="change" radius={[10, 10, 10, 10]} barSize={18}>
                {points.map((point) => (
                  <Cell
                    key={point.metricName}
                    fill={point.change >= 0 ? "#ff7a00" : "#fb7185"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="mt-6 grid gap-3">
          {points.map((point) => (
            <div
              key={point.metricName}
              className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4"
            >
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-white">{point.shortLabel}</p>
                  <p className="mt-2 text-sm text-muted-gray">
                    {point.samples} tracked value{point.samples === 1 ? "" : "s"}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold text-white">
                    {point.average.toFixed(2)}
                  </p>
                  <p className="text-xs uppercase tracking-[0.2em] text-muted-gray">
                    {point.unit}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </InfoCard>
  );
}
