"use client";

import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid
} from "recharts";

interface BudgetBreakdown {
  accommodation: number;
  food: number;
  transport_local: number;
  entrance_fee: number;
  misc: number;
}

interface BudgetData {
  destination: string;
  num_days: number;
  num_people: number;
  travel_style: string;
  breakdown_per_person_per_day: BudgetBreakdown;
  flight_estimate_total: number;
  subtotal: number;
  buffer_10pct: number;
  grand_total: number;
  grand_total_per_person: number;
  currency: string;
}

interface BudgetChartProps {
  data: BudgetData;
}

// Emerald / Teal theme
const COLORS = ["#10b981", "#34d399", "#059669", "#6ee7b7", "#047857"];
const LABEL_MAP: Record<string, string> = {
  accommodation: "🏨 Chỗ ở",
  food: "🍜 Ăn uống",
  transport_local: "🚗 Đi lại",
  entrance_fee: "🎟️ Vé tham quan",
  misc: "🛍️ Linh tinh",
};

const formatVND = (val: number) => {
  if (val >= 1_000_000) return `${(val / 1_000_000).toFixed(1)}M`;
  if (val >= 1_000) return `${(val / 1_000).toFixed(0)}K`;
  return val.toString();
};

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const d = payload[0];
    return (
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-3 text-sm shadow-lg">
        <p className="font-semibold text-emerald-600 dark:text-emerald-400">{d.name}</p>
        <p className="text-gray-800 dark:text-gray-200">{d.value.toLocaleString("vi-VN")} VNĐ</p>
      </div>
    );
  }
  return null;
};

export default function BudgetChart({ data }: BudgetChartProps) {
  const breakdown = data.breakdown_per_person_per_day;

  // Pie chart data (chi phí mỗi ngày/người)
  const pieData = Object.entries(breakdown).map(([key, value]) => ({
    name: LABEL_MAP[key] || key,
    value,
  }));

  // Bar chart data (tổng từng hạng mục * ngày * người)
  const barData = [
    ...Object.entries(breakdown).map(([key, value]) => ({
      name: LABEL_MAP[key] || key,
      value: value * data.num_days * data.num_people,
    })),
    ...(data.flight_estimate_total > 0
      ? [{ name: "✈️ Vé máy bay", value: data.flight_estimate_total }]
      : []),
    { name: "🛡️ Dự phòng 10%", value: data.buffer_10pct },
  ];

  return (
    <div className="budget-chart-container my-5 rounded-2xl border border-gray-200 dark:border-gray-700 bg-white/50 dark:bg-gray-800/50 p-5">
      {/* Header */}
      <div className="mb-5 border-b border-gray-100 dark:border-gray-700 pb-3">
        <h3 className="text-lg font-bold text-emerald-700 dark:text-emerald-400">
          💰 Ngân sách ước tính — {data.destination}
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          {data.num_days} ngày · {data.num_people} người · {data.travel_style}
        </p>
      </div>

      {/* Tổng tiền */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="rounded-xl bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-100 dark:border-emerald-800/30 p-4 text-center shadow-sm">
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Tổng chi phí</p>
          <p className="text-2xl font-bold text-emerald-700 dark:text-emerald-400">
            {data.grand_total.toLocaleString("vi-VN")}
          </p>
          <p className="text-xs font-medium text-emerald-600/70 dark:text-emerald-500 mt-1">VNĐ</p>
        </div>
        <div className="rounded-xl bg-teal-50 dark:bg-teal-900/20 border border-teal-100 dark:border-teal-800/30 p-4 text-center shadow-sm">
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Mỗi người</p>
          <p className="text-2xl font-bold text-teal-700 dark:text-teal-400">
            {data.grand_total_per_person.toLocaleString("vi-VN")}
          </p>
          <p className="text-xs font-medium text-teal-600/70 dark:text-teal-500 mt-1">VNĐ</p>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Pie Chart */}
        <div className="bg-gray-50 dark:bg-gray-900/30 rounded-xl p-3 border border-gray-100 dark:border-gray-800">
          <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 text-center mb-2 uppercase tracking-wide">
            Chi phí / người / ngày
          </p>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={85}
                paddingAngle={2}
                dataKey="value"
                stroke="none"
              >
                {pieData.map((_, index) => (
                  <Cell key={index} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend
                formatter={(value) => (
                  <span className="text-xs font-medium text-gray-600 dark:text-gray-300">{value}</span>
                )}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Bar Chart */}
        <div className="bg-gray-50 dark:bg-gray-900/30 rounded-xl p-3 border border-gray-100 dark:border-gray-800">
          <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 text-center mb-2 uppercase tracking-wide">
            Tổng theo hạng mục
          </p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={barData} layout="vertical" margin={{ left: 5, right: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" horizontal={false} />
              <XAxis
                type="number"
                tickFormatter={formatVND}
                tick={{ fill: "#9ca3af", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="name"
                tick={{ fill: "#6b7280", fontSize: 11, fontWeight: 500 }}
                width={95}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={16}>
                {barData.map((_, index) => (
                  <Cell key={index} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

