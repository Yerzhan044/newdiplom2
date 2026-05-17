import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

function CSVUpload() {
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setError(null);
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Пожалуйста, выберите CSV файл');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/csv/upload`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (data.success) {
        setResults(data.results);
        setFile(null);
      } else {
        setError(data.message);
      }
    } catch (err) {
      setError(`Ошибка загрузки: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const downloadTemplate = () => {
    const template = `sender_name,sender_country,sender_ip,receiver_name,receiver_country,receiver_ip,amount,currency,timestamp
Иван Иванов,KZ,192.168.1.10,John Smith,US,192.168.1.20,1000,USD,2026-05-17T10:00:00
Мария Петрова,RU,192.168.1.11,Jane Doe,DE,192.168.1.21,500,EUR,2026-05-17T11:00:00`;

    const blob = new Blob([template], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'transactions_template.csv';
    a.click();
  };

  const getStatusBadgeColor = (status) => {
    if (status === 'approved') return 'bg-green-900 text-green-200';
    if (status === 'blocked') return 'bg-red-900 text-red-200';
    if (status === 'review') return 'bg-yellow-900 text-yellow-200';
    return 'bg-gray-700 text-gray-200';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white">
      {/* Header */}
      <header className="bg-black bg-opacity-50 border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-3xl">📄</span>
              <h1 className="text-3xl font-bold">CSV Upload & Analysis</h1>
            </div>
            <button
              onClick={() => navigate('/')}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-bold transition"
            >
              ← Back to Dashboard
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Upload Section */}
        <div className="bg-slate-800 rounded-lg p-8 border border-blue-500 mb-8">
          <h2 className="text-2xl font-bold mb-6">📤 Upload CSV File</h2>

          <div className="space-y-4">
            {/* Instructions */}
            <div className="bg-slate-700 p-4 rounded border border-slate-600">
              <h3 className="text-blue-400 font-bold mb-2">CSV Format Requirements:</h3>
              <ul className="space-y-2 text-sm text-gray-300">
                <li>✓ <span className="font-mono">sender_name</span> - Имя отправителя</li>
                <li>✓ <span className="font-mono">sender_country</span> - Страна отправителя (ISO код)</li>
                <li>✓ <span className="font-mono">sender_ip</span> - IP адрес отправителя</li>
                <li>✓ <span className="font-mono">receiver_name</span> - Имя получателя</li>
                <li>✓ <span className="font-mono">receiver_country</span> - Страна получателя</li>
                <li>✓ <span className="font-mono">receiver_ip</span> - IP адрес получателя</li>
                <li>✓ <span className="font-mono">amount</span> - Сумма</li>
                <li>✓ <span className="font-mono">currency</span> - Валюта (USD, EUR, KZT, RUB)</li>
                <li>✓ <span className="font-mono">timestamp</span> - Время (ISO формат)</li>
              </ul>
            </div>

            {/* File Input */}
            <div className="border-2 border-dashed border-blue-500 rounded-lg p-8 text-center hover:border-blue-400 transition">
              <input
                type="file"
                accept=".csv"
                onChange={handleFileChange}
                className="hidden"
                id="csv-input"
              />
              <label htmlFor="csv-input" className="cursor-pointer">
                <div className="text-5xl mb-2">📁</div>
                <p className="text-lg font-bold">Click to select CSV file</p>
                <p className="text-sm text-gray-400">or drag and drop</p>
                {file && <p className="text-blue-400 mt-2 font-bold">✓ {file.name}</p>}
              </label>
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-red-900 border border-red-700 p-4 rounded text-red-200">
                ❌ {error}
              </div>
            )}

            {/* Buttons */}
            <div className="flex gap-4">
              <button
                onClick={handleUpload}
                disabled={!file || loading}
                className="flex-1 px-6 py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg font-bold transition"
              >
                {loading ? '⏳ Processing...' : '🚀 Upload & Analyze'}
              </button>
              <button
                onClick={downloadTemplate}
                className="flex-1 px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-bold transition"
              >
                📥 Download Template
              </button>
            </div>
          </div>
        </div>

        {/* Results Section */}
        {results.length > 0 && (
          <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-lg p-8 border-2 border-green-500 shadow-2xl">
            <div className="mb-8">
              <h2 className="text-3xl font-bold mb-2 bg-gradient-to-r from-green-400 to-blue-400 bg-clip-text text-transparent">
                ✅ Результаты анализа
              </h2>
              <p className="text-gray-400">Проанализировано {results.length} транзакций | {new Date().toLocaleString()}</p>
            </div>

            <div className="overflow-x-auto rounded-lg border border-gray-700 mb-8">
              <table className="w-full text-sm bg-slate-800">
                <thead>
                  <tr className="border-b-2 border-blue-600 bg-slate-900">
                    <th className="text-left py-4 px-4 font-bold text-blue-400">#</th>
                    <th className="text-left py-4 px-4 font-bold text-blue-400">От → К</th>
                    <th className="text-right py-4 px-4 font-bold text-blue-400">Сумма</th>
                    <th className="text-center py-4 px-4 font-bold text-blue-400">Риск (%)</th>
                    <th className="text-center py-4 px-4 font-bold text-blue-400">Статус</th>
                    <th className="text-left py-4 px-4 font-bold text-blue-400">Паттерны</th>
                    <th className="text-left py-4 px-4 font-bold text-blue-400">🤖 Объяснение</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((result, idx) => (
                    <tr key={idx} className={`border-b border-gray-700 transition ${
                      result.error ? 'bg-red-900 bg-opacity-20' :
                      result.status === 'blocked' ? 'bg-red-900 bg-opacity-20 hover:bg-red-900 hover:bg-opacity-30' :
                      result.status === 'review' ? 'bg-yellow-900 bg-opacity-20 hover:bg-yellow-900 hover:bg-opacity-30' :
                      'bg-green-900 bg-opacity-20 hover:bg-green-900 hover:bg-opacity-30'
                    }`}>
                      <td className="py-4 px-4 font-mono text-blue-300 font-bold">{result.row}</td>
                      <td className="py-4 px-4">
                        {result.error ? (
                          <span className="text-red-400 font-bold">❌ Ошибка</span>
                        ) : (
                          <div>
                            <div className="font-semibold text-sm text-white">{result.sender}</div>
                            <div className="text-xs text-gray-400">→ {result.receiver}</div>
                          </div>
                        )}
                      </td>
                      <td className="py-4 px-4 text-right font-bold text-white">
                        {result.error ? '-' : `${result.amount}\n${result.currency}`}
                      </td>
                      <td className="py-4 px-4 text-center font-mono font-bold">
                        {result.error ? '-' : (
                          <span className={`px-3 py-1 rounded-full text-white ${
                            result.fraud_score > 0.7 ? 'bg-red-600 text-white' :
                            result.fraud_score > 0.4 ? 'bg-yellow-600 text-white' :
                            'bg-green-600 text-white'
                          }`}>
                            {(result.fraud_score * 100).toFixed(0)}%
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-center">
                        {result.error ? (
                          <span className="px-3 py-1 rounded-full bg-red-900 text-red-200 text-xs font-bold">
                            ERROR
                          </span>
                        ) : (
                          <span className={`px-3 py-1 rounded-full text-xs font-bold ${getStatusBadgeColor(result.status)}`}>
                            {result.status.toUpperCase()}
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-xs">
                        {result.error ? '-' : (
                          <div className="space-y-1">
                            {result.patterns.slice(0, 2).map((p, i) => (
                              <div key={i} className="text-yellow-400">⚠️ {p}</div>
                            ))}
                            {result.patterns.length > 2 && (
                              <div className="text-gray-400">+{result.patterns.length - 2} more</div>
                            )}
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-4 text-xs text-gray-300">
                        {result.error ? (
                          <span className="text-red-400">{result.error}</span>
                        ) : (
                          result.explanation
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Summary Stats */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-gradient-to-br from-blue-900 to-blue-800 p-6 rounded-lg border border-blue-600 text-center shadow-lg hover:shadow-xl transition">
                <p className="text-gray-300 text-sm font-semibold mb-2">📊 Всего</p>
                <p className="text-4xl font-bold text-blue-300">
                  {results.filter(r => !r.error).length}
                </p>
                <p className="text-xs text-gray-400 mt-1">транзакций проанализировано</p>
              </div>
              <div className="bg-gradient-to-br from-green-900 to-green-800 p-6 rounded-lg border border-green-600 text-center shadow-lg hover:shadow-xl transition">
                <p className="text-gray-300 text-sm font-semibold mb-2">✅ Одобрено</p>
                <p className="text-4xl font-bold text-green-300">
                  {results.filter(r => r.status === 'approved').length}
                </p>
                <p className="text-xs text-gray-400 mt-1">{results.length > 0 ? ((results.filter(r => r.status === 'approved').length / results.filter(r => !r.error).length) * 100).toFixed(1) : 0}%</p>
              </div>
              <div className="bg-gradient-to-br from-yellow-900 to-yellow-800 p-6 rounded-lg border border-yellow-600 text-center shadow-lg hover:shadow-xl transition">
                <p className="text-gray-300 text-sm font-semibold mb-2">⚠️  На проверку</p>
                <p className="text-4xl font-bold text-yellow-300">
                  {results.filter(r => r.status === 'review').length}
                </p>
                <p className="text-xs text-gray-400 mt-1">{results.length > 0 ? ((results.filter(r => r.status === 'review').length / results.filter(r => !r.error).length) * 100).toFixed(1) : 0}%</p>
              </div>
              <div className="bg-gradient-to-br from-red-900 to-red-800 p-6 rounded-lg border border-red-600 text-center shadow-lg hover:shadow-xl transition">
                <p className="text-gray-300 text-sm font-semibold mb-2">🚫 Заблокировано</p>
                <p className="text-4xl font-bold text-red-300">
                  {results.filter(r => r.status === 'blocked').length}
                </p>
                <p className="text-xs text-gray-400 mt-1">{results.length > 0 ? ((results.filter(r => r.status === 'blocked').length / results.filter(r => !r.error).length) * 100).toFixed(1) : 0}%</p>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-black bg-opacity-50 border-t border-gray-700 mt-12">
        <div className="max-w-7xl mx-auto px-6 py-6 text-center text-gray-400">
          <p>Fraud Detection System © 2026 | CSV Upload & Analysis</p>
        </div>
      </footer>
    </div>
  );
}

export default CSVUpload;
