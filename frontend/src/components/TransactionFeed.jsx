import React, { useState } from 'react';

function TransactionFeed({ transactions, onSelectTransaction }) {
  const [loadingTxnId, setLoadingTxnId] = useState(null);

  const getStatusColor = (status) => {
    if (status === 'approved') return 'bg-green-900 text-green-200';
    if (status === 'review') return 'bg-yellow-900 text-yellow-200';
    if (status === 'blocked') return 'bg-red-900 text-red-200';
    return 'bg-gray-600 text-gray-200';
  };

  const getStatusLabel = (status) => {
    if (status === 'approved') return '✅ APPROVED';
    if (status === 'review') return '⚠️ REVIEW';
    if (status === 'blocked') return '❌ BLOCKED';
    return '⏳ PENDING';
  };

  const handleRowClick = async (txn) => {
    try {
      setLoadingTxnId(txn.transaction_id);
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/transactions/${txn.transaction_id}`);
      const fullTxn = await response.json();

      // Получаем fraud score если есть
      let fraudData = {};
      try {
        const fraudResponse = await fetch(`${apiUrl}/api/transactions/${txn.transaction_id}/fraud-score`);
        fraudData = await fraudResponse.json();
      } catch (e) {
        console.log('Fraud score not found');
      }

      // Получаем паттерны если есть
      let patterns = [];
      try {
        const patternsResponse = await fetch(`${apiUrl}/api/transactions/${txn.transaction_id}/patterns`);
        const patternsData = await patternsResponse.json();
        if (Array.isArray(patternsData)) {
          patterns = patternsData.map(p => p.pattern_name || p);
        }
      } catch (e) {
        console.log('Patterns not found');
      }

      // Объединяем все данные
      const enrichedTxn = {
        ...txn,
        fraud_score: fraudData.final_score || txn.fraud_score,
        ml_scores: fraudData ? {
          'XGBoost': fraudData.xgboost_score,
          'Random Forest': fraudData.random_forest_score,
          'LSTM': fraudData.lstm_score,
          'Isolation Forest': fraudData.isolation_forest_score,
          'Rule Engine': fraudData.rule_engine_score,
        } : {},
        explanation: fraudData.explanation || txn.explanation,
        patterns: patterns || txn.patterns || [],
      };

      onSelectTransaction(enrichedTxn);
    } catch (error) {
      console.error('Error fetching transaction details:', error);
      onSelectTransaction(txn);
    } finally {
      setLoadingTxnId(null);
    }
  };

  return (
    <div className="stat-card">
      <h2 className="text-xl font-bold mb-4">📊 Live Transaction Feed</h2>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-600">
              <th className="text-left py-3 px-4">ID</th>
              <th className="text-left py-3 px-4">From → To</th>
              <th className="text-right py-3 px-4">Amount</th>
              <th className="text-center py-3 px-4">Status</th>
              <th className="text-right py-3 px-4">Time</th>
            </tr>
          </thead>
          <tbody>
            {transactions.length === 0 ? (
              <tr>
                <td colSpan="5" className="text-center py-8 text-gray-400">
                  ⏳ Waiting for transactions...
                </td>
              </tr>
            ) : (
              transactions.map((txn, idx) => (
                <tr
                  key={idx}
                  onClick={() => handleRowClick(txn)}
                  className="border-b border-gray-700 hover:bg-gray-800 transition cursor-pointer"
                >
                  <td className="py-3 px-4 font-mono text-xs text-blue-400">
                    #{txn.transaction_id}
                  </td>
                  <td className="py-3 px-4 text-sm">
                    <div className="font-semibold">{txn.sender}</div>
                    <div className="text-xs text-gray-400">→ {txn.receiver}</div>
                  </td>
                  <td className="py-3 px-4 text-right font-semibold">
                    {txn.amount.toFixed(2)} {txn.currency}
                  </td>
                  <td className="py-3 px-4 text-center">
                    <span className={`px-3 py-1 rounded-full text-xs font-bold ${getStatusColor(txn.status)}`}>
                      {getStatusLabel(txn.status)}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right text-xs text-gray-400">
                    {txn.timestamp}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default TransactionFeed;
