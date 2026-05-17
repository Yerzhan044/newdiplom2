import React from 'react';

function TopPatterns({ patterns }) {
  const patternEmojis = {
    night_transfer: '🌙',
    velocity_attack: '⚡',
    structuring: '📦',
    same_amount_multiple_senders: '💰',
    spending_surge: '📈',
    amount_splitting: '✂️',
    informal_business: '🏪',
    frequent_international: '🌍',
    vpn_location_mismatch: '🔐',
    impossible_movement: '✈️',
    card_activity_spike: '🔥',
    immediate_withdrawal: '💸',
  };

  return (
    <div className="stat-card">
      <h2 className="text-xl font-bold mb-4">🚨 Top Fraud Patterns</h2>

      {patterns.length === 0 ? (
        <div className="text-gray-400 text-center py-8">
          <p>No patterns detected yet</p>
          <p className="text-xs mt-2">Patterns will appear as transactions are processed</p>
        </div>
      ) : (
        <div className="space-y-3">
          {patterns.slice(0, 5).map((pattern, idx) => (
            <div
              key={idx}
              className="bg-gray-700 bg-opacity-50 p-3 rounded-lg border-l-4 border-red-500"
            >
              <div className="flex items-start gap-2">
                <span className="text-lg mt-1">
                  {patternEmojis[pattern.name] || '⚠️'}
                </span>
                <div className="flex-1">
                  <div className="font-semibold text-sm">
                    {pattern.name.replace(/_/g, ' ')}
                  </div>
                  <div className="text-xs text-gray-400 mt-1">
                    Detected: {pattern.count || 1} times
                  </div>
                  <div className="mt-2 bg-red-900 bg-opacity-30 rounded px-2 py-1">
                    <div className="text-xs text-red-200">
                      Confidence: {((pattern.confidence || 0.7) * 100).toFixed(0)}%
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-6 pt-4 border-t border-gray-600">
        <div className="text-xs text-gray-500 text-center">
          Last updated: {new Date().toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
}

export default TopPatterns;
