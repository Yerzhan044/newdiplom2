import React, { useState, useEffect, useRef } from 'react';
import { Routes, Route, useNavigate, Navigate } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext';
import TransactionFeed from './components/TransactionFeed';
import StatisticsPanel from './components/StatisticsPanel';
import TopPatterns from './components/TopPatterns';
import InteractionGraph from './components/InteractionGraph';
import CSVUpload from './pages/CSVUpload';
import ClientApp from './pages/ClientApp';
import LoginPage from './pages/LoginPage';
import './App.css';

// Protected Route Component
function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white flex items-center justify-center">
        <div className="text-center">
          <p className="text-2xl font-bold mb-4">⏳ Загрузка...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

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
  const [activeTab, setActiveTab] = useState('dashboard'); // 'dashboard' или 'graph'
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
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/client"
        element={
          <ProtectedRoute>
            <ClientApp />
          </ProtectedRoute>
        }
      />
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
                      onClick={() => navigate('/client')}
                      className="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg font-bold transition"
                    >
                      📱 Клиент
                    </button>
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

            {/* Tab Navigation */}
            <div className="bg-black bg-opacity-50 border-b border-gray-700 sticky top-0 z-40">
              <div className="max-w-7xl mx-auto px-6">
                <div className="flex gap-4">
                  <button
                    onClick={() => setActiveTab('dashboard')}
                    className={`px-6 py-4 font-bold transition border-b-2 ${
                      activeTab === 'dashboard'
                        ? 'border-blue-500 text-blue-400'
                        : 'border-transparent text-gray-400 hover:text-white'
                    }`}
                  >
                    📊 Dashboard
                  </button>
                  <button
                    onClick={() => setActiveTab('graph')}
                    className={`px-6 py-4 font-bold transition border-b-2 ${
                      activeTab === 'graph'
                        ? 'border-blue-500 text-blue-400'
                        : 'border-transparent text-gray-400 hover:text-white'
                    }`}
                  >
                    🌐 Interaction Graph
                  </button>
                </div>
              </div>
            </div>

      {/* Main Content */}
      <main className="max-w-full mx-auto px-6 py-8">
        {activeTab === 'dashboard' ? (
          <>
            {/* Dashboard View */}
            <div className="max-w-7xl mx-auto">
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
            </div>
          </>
        ) : (
          <>
            {/* Graph View */}
            <div className="h-screen -mx-6 -my-8">
              <InteractionGraph apiUrl={process.env.REACT_APP_API_URL || 'http://localhost:8000'} />
            </div>
          </>
        )}

        {/* AI Explanation Modal - Expanded */}
        {selectedTransaction && activeTab === 'dashboard' && (
          <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center p-4 z-50 overflow-y-auto">
            <div className="bg-slate-800 rounded-lg p-8 max-w-4xl w-full border-2 border-blue-500 my-8">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-3xl font-bold text-white">🔍 Detailed Transaction Analysis</h2>
                <button
                  onClick={() => setSelectedTransaction(null)}
                  className="text-gray-400 hover:text-white text-4xl leading-none"
                >
                  ×
                </button>
              </div>

              <div className="space-y-5">
                {/* Transaction Overview */}
                <div className="bg-slate-700 p-4 rounded border border-slate-600">
                  <h3 className="text-blue-400 font-bold mb-3">📊 Transaction Overview</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <p className="text-gray-400 text-xs font-bold">FROM</p>
                      <p className="text-white font-semibold">{selectedTransaction.sender}</p>
                    </div>
                    <div>
                      <p className="text-gray-400 text-xs font-bold">TO</p>
                      <p className="text-white font-semibold">{selectedTransaction.receiver}</p>
                    </div>
                    <div>
                      <p className="text-gray-400 text-xs font-bold">AMOUNT</p>
                      <p className="text-white font-semibold">{selectedTransaction.amount} {selectedTransaction.currency}</p>
                    </div>
                    <div>
                      <p className="text-gray-400 text-xs font-bold">TIME</p>
                      <p className="text-white font-semibold text-sm">{selectedTransaction.timestamp}</p>
                    </div>
                  </div>
                </div>

                {/* ML Model Scores */}
                {selectedTransaction.ml_scores && (
                  <div className="bg-slate-700 p-4 rounded border border-purple-600">
                    <h3 className="text-purple-400 font-bold mb-3">🤖 ML Model Predictions</h3>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                      {Object.entries(selectedTransaction.ml_scores).map(([model, score]) => (
                        <div key={model} className="bg-slate-600 p-3 rounded">
                          <p className="text-gray-400 text-xs font-bold uppercase">{model.replace('_', ' ')}</p>
                          <div className="flex items-baseline gap-2 mt-1">
                            <p className="text-xl font-bold">{typeof score === 'number' ? score.toFixed(3) : 'N/A'}</p>
                            {typeof score === 'number' && (
                              <div className="h-2 flex-1 bg-gray-500 rounded overflow-hidden">
                                <div
                                  className={`h-full ${
                                    score >= 0.6 ? 'bg-red-500' :
                                    score >= 0.35 ? 'bg-yellow-500' :
                                    'bg-green-500'
                                  }`}
                                  style={{ width: `${score * 100}%` }}
                                />
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Fraud Score Bar */}
                <div className="bg-slate-700 p-4 rounded border-2 border-orange-600">
                  <h3 className="text-orange-400 font-bold mb-3">🚨 Final Fraud Score</h3>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-white font-semibold">{selectedTransaction.fraud_score?.toFixed(4) || 'N/A'}</span>
                      <span className="text-gray-400 text-sm">
                        Threshold: {selectedTransaction.status === 'blocked' ? '≥0.60' :
                                   selectedTransaction.status === 'review' ? '0.35-0.60' :
                                   '<0.35'}
                      </span>
                    </div>
                    <div className="h-4 bg-gray-600 rounded overflow-hidden">
                      <div
                        className={`h-full transition-all ${
                          selectedTransaction.fraud_score >= 0.6 ? 'bg-red-500' :
                          selectedTransaction.fraud_score >= 0.35 ? 'bg-yellow-500' :
                          'bg-green-500'
                        }`}
                        style={{ width: `${(selectedTransaction.fraud_score || 0) * 100}%` }}
                      />
                    </div>
                  </div>
                </div>

                {/* Detected Patterns */}
                {selectedTransaction.patterns && selectedTransaction.patterns.length > 0 && (
                  <div className="bg-slate-700 p-4 rounded border border-yellow-600">
                    <h3 className="text-yellow-400 font-bold mb-3">⚠️ Detected Fraud Patterns</h3>
                    <ul className="space-y-2">
                      {selectedTransaction.patterns.map((pattern, idx) => (
                        <li key={idx} className="bg-slate-600 p-3 rounded border-l-2 border-yellow-500">
                          <p className="text-yellow-200 font-semibold">{pattern}</p>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* AI Explanation */}
                <div className="bg-slate-700 p-4 rounded border border-blue-600">
                  <h3 className="text-blue-400 font-bold mb-3">💬 AI Analysis (Groq)</h3>
                  <p className="text-gray-200 leading-relaxed text-sm">
                    {selectedTransaction.explanation || 'No explanation available'}
                  </p>
                </div>

                {/* Status */}
                <div className={`p-4 rounded font-bold text-lg text-center border-2 ${
                  selectedTransaction.status === 'approved' ? 'bg-green-900 text-green-200 border-green-700' :
                  selectedTransaction.status === 'blocked' ? 'bg-red-900 text-red-200 border-red-700' :
                  selectedTransaction.status === 'review' ? 'bg-yellow-900 text-yellow-200 border-yellow-700' :
                  'bg-gray-700 text-gray-200 border-gray-600'
                }`}>
                  STATUS: {selectedTransaction.status?.toUpperCase() || 'UNKNOWN'}
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
