import React from 'react';

function StatisticsPanel({ statistics }) {
  const total = statistics.total || 1;
  const approvedRate = ((statistics.approved / total) * 100).toFixed(1);
  const reviewRate = ((statistics.review / total) * 100).toFixed(1);
  const blockedRate = ((statistics.blocked / total) * 100).toFixed(1);

  const StatCard = ({ label, value, color, rate }) => (
    <div className="stat-card">
      <div className={`text-3xl font-bold ${color}`}>{value}</div>
      <div className="metric-label">{label}</div>
      <div className="text-xs text-gray-400 mt-2">{rate}% of total</div>
    </div>
  );

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <StatCard
        label="Total Transactions"
        value={statistics.total}
        color="text-blue-400"
        rate="100"
      />
      <StatCard
        label="✅ Approved"
        value={statistics.approved}
        color="text-green-400"
        rate={approvedRate}
      />
      <StatCard
        label="⚠️ Under Review"
        value={statistics.review}
        color="text-yellow-400"
        rate={reviewRate}
      />
      <StatCard
        label="❌ Blocked"
        value={statistics.blocked}
        color="text-red-400"
        rate={blockedRate}
      />
    </div>
  );
}

export default StatisticsPanel;
