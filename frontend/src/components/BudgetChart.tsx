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

const COLORS = ["#6366f1", "#8b5cf6", "#a78bfa", "#c4b5fd", "#ddd6fe"];
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
      <div className="bg-gray-900 border border-purple-500/30 rounded-lg p-3 text-sm shadow-xl">
        <p className="font-semibold text-purple-300">{d.name}</p>
        <p className="text-white">{d.value.toLocaleString("vi-VN")} VNĐ/người/ngày</p>
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
    <div className="budget-chart-container my-4 rounded-2xl border border-purple-500/20 bg-gray-900/60 backdrop-blur-sm p-5">
      {/* Header */}
      <div className="mb-4">
        <h3 className="text-lg font-bold text-purple-300">
          💰 Ngân sách ước tính — {data.destination}
        </h3>
        <p className="text-sm text-gray-400 mt-1">
          {data.num_days} ngày · {data.num_people} người · {data.travel_style}
        </p>
      </div>

      {/* Tổng tiền */}
      <div className="grid grid-cols-2 gap-3 mb-5">
        <div className="rounded-xl bg-purple-900/40 border border-purple-500/30 p-3 text-center">
          <p className="text-xs text-gray-400 mb-1">Tổng chi phí</p>
          <p className="text-xl font-bold text-white">
            {data.grand_total.toLocaleString("vi-VN")}
          </p>
          <p className="text-xs text-purple-400">VNĐ</p>
        </div>
        <div className="rounded-xl bg-indigo-900/40 border border-indigo-500/30 p-3 text-center">
          <p className="text-xs text-gray-400 mb-1">Mỗi người</p>
          <p className="text-xl font-bold text-white">
            {data.grand_total_per_person.toLocaleString("vi-VN")}
          </p>
          <p className="text-xs text-indigo-400">VNĐ</p>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Pie Chart */}
        <div>
          <p className="text-xs text-gray-500 text-center mb-2">Chi phí/người/ngày</p>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={80}
                paddingAngle={3}
                dataKey="value"
              >
                {pieData.map((_, index) => (
                  <Cell key={index} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend
                formatter={(value) => (
                  <span className="text-xs text-gray-300">{value}</span>
                )}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Bar Chart */}
        <div>
          <p className="text-xs text-gray-500 text-center mb-2">Tổng theo hạng mục (VNĐ)</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={barData} layout="vertical" margin={{ left: 10, right: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                type="number"
                tickFormatter={formatVND}
                tick={{ fill: "#9ca3af", fontSize: 10 }}
              />
              <YAxis
                type="category"
                dataKey="name"
                tick={{ fill: "#9ca3af", fontSize: 10 }}
                width={90}
              />
              <Tooltip
                formatter={(val: any) => [`${Number(val).toLocaleString("vi-VN")} VNĐ`, ""]}
                contentStyle={{ background: "#111827", border: "1px solid #7c3aed33" }}
                labelStyle={{ color: "#a78bfa" }}
              />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>
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
