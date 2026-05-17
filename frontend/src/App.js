import React, { useState, useEffect, useRef } from 'react';
import { Routes, Route, useNavigate } from 'react-router-dom';
import TransactionFeed from './components/TransactionFeed';
import StatisticsPanel from './components/StatisticsPanel';
import TopPatterns from './components/TopPatterns';
import CSVUpload from './pages/CSVUpload';
import './App.css';

function App() {
  const navigate = useNavigate();
  const [transactions, setTransactions] = useState([]);
  const [statistics, setStatistics] = useState({
    total: 0,
    approved: 0,
    review: 0,
    blocked: 0,
  });
  const [topPatterns, setTopPatterns] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [selectedTransaction, setSelectedTransaction] = useState(null);
  const wsRef = useRef(null);

  useEffect(() => {
    // Подключение к WebSocket
    const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    const wsUrl = apiUrl.replace('http', 'ws') + '/ws/transactions';

    const connectWebSocket = () => {
      try {
        wsRef.current = new WebSocket(wsUrl);

        wsRef.current.onopen = () => {
          console.log('✅ WebSocket подключён');
          setIsConnected(true);
        };

        wsRef.current.onmessage = (event) => {
          const data = JSON.parse(event.data);

          if (data.type === 'transaction') {
            // Добавляем новую транзакцию в начало списка
            setTransactions(prev => [data.data, ...prev.slice(0, 99)]);
          } else if (data.type === 'statistics') {
            // Обновляем статистику
            setStatistics(data.data);
          } else if (data.type === 'fraud_pattern') {
            // Обновляем паттерны (опционально)
            console.log('🚨 Pattern alert:', data.data);
          }
        };

        wsRef.current.onerror = (error) => {
          console.error('❌ WebSocket ошибка:', error);
          setIsConnected(false);
        };

        wsRef.current.onclose = () => {
          console.log('❌ WebSocket закрыт');
          setIsConnected(false);
          // Переподключение через 3 сек
          setTimeout(connectWebSocket, 3000);
        };
      } catch (error) {
        console.error('Ошибка подключения:', error);
      }
    };

    connectWebSocket();

    // Загружаем начальные данные
    fetchStatistics();
    fetchTransactions();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const fetchStatistics = async () => {
    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/transactions/stats/general`);
      const data = await response.json();

      setStatistics({
        total: data.total_transactions,
        approved: data.approved_count,
        review: data.review_count,
        blocked: data.blocked_count,
      });
    } catch (error) {
      console.error('Ошибка загрузки статистики:', error);
    }
  };

  const fetchTransactions = async () => {
    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/transactions/?limit=50`);
      const data = await response.json();

      // Преобразуем в нужный формат
      const formatted = data.map(txn => ({
        transaction_id: txn.id,
        sender: `User ${txn.sender_id}`,
        receiver: `User ${txn.receiver_id}`,
        amount: txn.amount,
        currency: txn.currency,
        status: txn.status,
        timestamp: new Date(txn.timestamp).toLocaleString(),
      }));

      setTransactions(formatted);
    } catch (error) {
      console.error('Ошибка загрузки транзакций:', error);
    }
  };

  return (
    <Routes>
      <Route path="/csv-upload" element={<CSVUpload />} />
      <Route
        path="/"
        element={
          <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white">
            {/* Header */}
            <header className="bg-black bg-opacity-50 border-b border-gray-700">
              <div className="max-w-7xl mx-auto px-6 py-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-3xl">🛡️</span>
                    <h1 className="text-3xl font-bold">Fraud Detection System</h1>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                      <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
                      <span>{isConnected ? 'Live' : 'Offline'}</span>
                    </div>
                    <button
                      onClick={() => navigate('/csv-upload')}
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-bold transition"
                    >
                      📤 CSV Upload
                    </button>
                  </div>
                </div>
              </div>
            </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Statistics Grid */}
        <StatisticsPanel statistics={statistics} />

        {/* Two Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-8">
          {/* Transaction Feed (2 columns) */}
          <div className="lg:col-span-2">
            <TransactionFeed transactions={transactions} onSelectTransaction={setSelectedTransaction} />
          </div>

          {/* Top Patterns (1 column) */}
          <div>
            <TopPatterns patterns={topPatterns} />
          </div>
        </div>

        {/* AI Explanation Modal */}
        {selectedTransaction && (
          <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center p-4 z-50">
            <div className="bg-slate-800 rounded-lg p-8 max-w-2xl w-full max-h-96 overflow-y-auto border-2 border-blue-500">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-white">🤖 AI Explanation</h2>
                <button
                  onClick={() => setSelectedTransaction(null)}
                  className="text-gray-400 hover:text-white text-3xl leading-none"
                >
                  ×
                </button>
              </div>

              <div className="space-y-4">
                <div className="bg-slate-700 p-4 rounded border border-slate-600">
                  <h3 className="text-blue-400 font-bold mb-2">📊 Transaction</h3>
                  <p className="text-gray-300 text-sm">
                    {selectedTransaction.sender} → {selectedTransaction.receiver}
                  </p>
                  <p className="text-gray-300 text-sm">
                    <span className="font-semibold">{selectedTransaction.amount}</span> {selectedTransaction.currency}
                  </p>
                </div>

                <div className="bg-slate-700 p-4 rounded border border-blue-600">
                  <h3 className="text-blue-400 font-bold mb-2">💬 AI Analysis</h3>
                  <p className="text-gray-200 leading-relaxed text-sm">
                    {selectedTransaction.explanation || 'No explanation available'}
                  </p>
                </div>

                {selectedTransaction.patterns && selectedTransaction.patterns.length > 0 && (
                  <div className="bg-slate-700 p-4 rounded border border-yellow-600">
                    <h3 className="text-yellow-400 font-bold mb-2">⚠️ Detected Patterns</h3>
                    <ul className="space-y-1">
                      {selectedTransaction.patterns.map((pattern, idx) => (
                        <li key={idx} className="text-gray-300 text-sm">
                          • {pattern}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className={`p-4 rounded font-bold text-center ${
                  selectedTransaction.status === 'approved' ? 'bg-green-900 text-green-200 border border-green-700' :
                  selectedTransaction.status === 'blocked' ? 'bg-red-900 text-red-200 border border-red-700' :
                  selectedTransaction.status === 'review' ? 'bg-yellow-900 text-yellow-200 border border-yellow-700' :
                  'bg-gray-700 text-gray-200'
                }`}>
                  Status: {selectedTransaction.status.toUpperCase()}
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

            {/* Footer */}
            <footer className="bg-black bg-opacity-50 border-t border-gray-700 mt-12">
              <div className="max-w-7xl mx-auto px-6 py-6 text-center text-gray-400">
                <p>Fraud Detection System © 2026 | Real-time ML-based detection</p>
              </div>
            </footer>
          </div>
        }
      />
    </Routes>
  );
}

export default App;
