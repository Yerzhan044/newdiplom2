import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

function ClientApp() {
  const navigate = useNavigate();
  const { user, token, logout } = useAuth();

  const [userAccounts, setUserAccounts] = useState([]);
  const [allUsers, setAllUsers] = useState([]);
  const [senderAccount, setSenderAccount] = useState(null);
  const [receiverUser, setReceiverUser] = useState(null);
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('Transfer');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [transactionResult, setTransactionResult] = useState(null);
  const [transactions, setTransactions] = useState([]);

  // Fraud Simulation Mode
  const [fraudMode, setFraudMode] = useState(false);
  const [vpnFlag, setVpnFlag] = useState(false);
  const [geoMismatch, setGeoMismatch] = useState(false);
  const [nightTime, setNightTime] = useState(false);
  const [structuring, setStructuring] = useState(false);
  const [velocityAttack, setVelocityAttack] = useState(false);
  const [velocityCount, setVelocityCount] = useState(5);
  const [velocitySeconds, setVelocitySeconds] = useState(30);
  const [velocityProgress, setVelocityProgress] = useState(null);

  // Load user data on mount
  useEffect(() => {
    fetchUserAccounts();
    fetchAllUsers();
  }, []);

  const fetchUserAccounts = async () => {
    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/auth/me`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });

      const data = await response.json();

      if (data.success) {
        setUserAccounts(data.accounts);
        if (data.accounts.length > 0) {
          setSenderAccount(data.accounts[0]);
        }
      }
    } catch (err) {
      console.error('Ошибка загрузки аккаунтов:', err);
    }
  };

  const fetchAllUsers = async () => {
    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/auth/users`);
      const data = await response.json();

      if (data.success) {
        // Filter out current user
        const otherUsers = data.users.filter(u => u.id !== user.id);
        setAllUsers(otherUsers);
        if (otherUsers.length > 0) {
          setReceiverUser(otherUsers[0].id);
        }
      }
    } catch (err) {
      console.error('Ошибка загрузки пользователей:', err);
    }
  };

  // Preset scenarios
  const applyPreset = (preset) => {
    setFraudMode(preset !== 'normal');
    setVpnFlag(false);
    setGeoMismatch(false);
    setNightTime(false);
    setStructuring(false);
    setVelocityAttack(false);

    if (preset === 'normal') {
      setAmount(Math.floor(Math.random() * (50000 - 5000) + 5000).toString());
      setDescription('Regular transfer');
    } else if (preset === 'suspicious') {
      setAmount('99500');
      setDescription('Suspicious transfer');
      setNightTime(true);
    } else if (preset === 'fraud') {
      setAmount('99999');
      setDescription('Obvious fraud');
      setVpnFlag(true);
      setGeoMismatch(true);
      setStructuring(true);
      setVelocityAttack(true);
    }
  };

  const handleSendTransfer = async () => {
    if (!senderAccount) {
      setError('Выберите счет отправителя');
      return;
    }
    if (!receiverUser) {
      setError('Выберите получателя');
      return;
    }
    if (!amount || parseFloat(amount) <= 0) {
      setError('Введите корректную сумму');
      return;
    }

    if (velocityAttack && velocityCount > 1) {
      setError(null);
      await handleVelocityAttack();
      return;
    }

    await sendSingleTransfer();
  };

  const sendSingleTransfer = async () => {
    setLoading(true);
    setError(null);

    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const timestamp = nightTime
        ? new Date(new Date().setHours(3, 0, 0, 0)).toISOString()
        : new Date().toISOString();

      const response = await fetch(
        `${apiUrl}/api/accounts/${senderAccount.id}/transfer?` +
        `receiver_user_id=${receiverUser}&amount=${amount}&description=${description}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({
            vpn_flag: vpnFlag,
            geo_mismatch: geoMismatch,
            timestamp: timestamp,
          })
        }
      );

      const data = await response.json();

      if (data.success) {
        const receiverName = allUsers.find(u => u.id === receiverUser)?.name || 'Unknown';
        const result = {
          id: data.transaction_id,
          status: data.status,
          fraud_score: data.fraud_score,
          explanation: data.explanation,
          timestamp: new Date().toLocaleTimeString(),
          sender: user.username,
          receiver: receiverName,
          amount: amount,
          currency: senderAccount.currency,
        };

        setTransactionResult(result);
        setTransactions([result, ...transactions.slice(0, 4)]);
        setAmount('');
        setDescription('Transfer');
        setSenderAccount(null);
        setReceiverUser(null);
        setFraudMode(false);
        resetFraudFlags();
        fetchUserAccounts();
      } else {
        setError(`Ошибка: ${data.message || 'Неизвестная ошибка'}`);
      }
    } catch (err) {
      console.error('Ошибка при отправке перевода:', err);
      setError(`Ошибка: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleVelocityAttack = async () => {
    setLoading(true);
    setVelocityProgress({ current: 0, total: velocityCount });

    const delay = (velocitySeconds * 1000) / velocityCount;

    for (let i = 0; i < velocityCount; i++) {
      await new Promise(resolve => setTimeout(resolve, delay));

      try {
        const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
        const response = await fetch(
          `${apiUrl}/api/accounts/${senderAccount.id}/transfer?` +
          `receiver_user_id=${receiverUser}&amount=${amount}&description=${description} (${i + 1}/${velocityCount})`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${token}`
            },
            body: JSON.stringify({
              vpn_flag: vpnFlag,
              geo_mismatch: geoMismatch,
              velocity: velocityCount,
            })
          }
        );

        const data = await response.json();

        if (data.success) {
          const receiverName = allUsers.find(u => u.id === receiverUser)?.name || 'Unknown';
          const result = {
            id: data.transaction_id,
            status: data.status,
            fraud_score: data.fraud_score,
            timestamp: new Date().toLocaleTimeString(),
            sender: user.username,
            receiver: receiverName,
            amount: amount,
            currency: senderAccount.currency,
          };

          setTransactions(prev => [result, ...prev.slice(0, 4)]);
        }
      } catch (err) {
        console.error(`Ошибка в транзакции ${i + 1}:`, err);
      }

      setVelocityProgress({ current: i + 1, total: velocityCount });
    }

    setLoading(false);
    setVelocityProgress(null);
    setVelocityAttack(false);
    resetFraudFlags();
    setAmount('');
    setSenderAccount(null);
    setReceiverUser(null);
    fetchUserAccounts();
  };

  const resetFraudFlags = () => {
    setVpnFlag(false);
    setGeoMismatch(false);
    setNightTime(false);
    setStructuring(false);
    setVelocityAttack(false);
  };

  const getStatusColor = (status) => {
    if (status === 'approved') return { bg: 'bg-green-900', border: 'border-green-600', text: 'text-green-300', icon: '✅' };
    if (status === 'blocked') return { bg: 'bg-red-900', border: 'border-red-600', text: 'text-red-300', icon: '❌' };
    if (status === 'review') return { bg: 'bg-yellow-900', border: 'border-yellow-600', text: 'text-yellow-300', icon: '⚠️' };
    return { bg: 'bg-gray-900', border: 'border-gray-600', text: 'text-gray-300', icon: '❓' };
  };

  const getFraudScoreColor = (score) => {
    if (score < 0.4) return 'bg-green-600';
    if (score < 0.7) return 'bg-yellow-600';
    return 'bg-red-600';
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white">
      {/* Header */}
      <header className="bg-black bg-opacity-50 border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-3xl">📱</span>
              <div>
                <h1 className="text-3xl font-bold">Клиент: {user?.username}</h1>
                <p className="text-sm text-gray-400">Демонстрация системы обнаружения мошенничества</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => navigate('/')}
                className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-bold transition"
              >
                ← На главную
              </button>
              <button
                onClick={handleLogout}
                className="px-6 py-2 bg-red-600 hover:bg-red-700 rounded-lg font-bold transition"
              >
                🚪 Выход
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Transfer Form - Left Side */}
          <div className="lg:col-span-2 space-y-6">
            {/* Fraud Mode Toggle */}
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">🚨</span>
                  <div>
                    <h3 className="font-bold text-lg">Режим симуляции мошенничества</h3>
                    <p className="text-xs text-gray-400">Включи для добавления fraud паттернов</p>
                  </div>
                </div>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={fraudMode}
                    onChange={(e) => {
                      setFraudMode(e.target.checked);
                      if (!e.target.checked) resetFraudFlags();
                    }}
                    className="w-6 h-6"
                  />
                  <span className={`px-4 py-2 rounded font-bold transition ${fraudMode ? 'bg-red-600' : 'bg-green-600'}`}>
                    {fraudMode ? 'ВКЛ' : 'ВЫКЛ'}
                  </span>
                </label>
              </div>
            </div>

            {/* Quick Presets */}
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <h3 className="font-bold mb-4">⚡ Быстрые сценарии</h3>
              <div className="grid grid-cols-3 gap-3">
                <button
                  onClick={() => applyPreset('normal')}
                  className="bg-green-600 hover:bg-green-700 p-4 rounded-lg font-bold transition flex flex-col items-center gap-2"
                >
                  <span className="text-2xl">🟢</span>
                  <span>Нормальный</span>
                  <span className="text-xs text-gray-200">(5k-50k USD)</span>
                </button>
                <button
                  onClick={() => applyPreset('suspicious')}
                  className="bg-yellow-600 hover:bg-yellow-700 p-4 rounded-lg font-bold transition flex flex-col items-center gap-2"
                >
                  <span className="text-2xl">🟡</span>
                  <span>Подозрительный</span>
                  <span className="text-xs text-gray-200">(99.5k ночью)</span>
                </button>
                <button
                  onClick={() => applyPreset('fraud')}
                  className="bg-red-600 hover:bg-red-700 p-4 rounded-lg font-bold transition flex flex-col items-center gap-2"
                >
                  <span className="text-2xl">🔴</span>
                  <span>Явное мошенничество</span>
                  <span className="text-xs text-gray-200">(VPN + Geo + Velocity)</span>
                </button>
              </div>
            </div>

            {/* Transfer Form */}
            <div className={`bg-slate-800 rounded-lg p-8 border-2 transition ${fraudMode ? 'border-red-500' : 'border-blue-500'}`}>
              <h2 className={`text-2xl font-bold mb-6 ${fraudMode ? 'text-red-400' : 'text-blue-400'}`}>
                {fraudMode ? '🚨 Отправить fraud транзакцию' : '💸 Отправить перевод'}
              </h2>

              {error && (
                <div className="bg-red-900 border border-red-700 p-4 rounded mb-4 text-red-200">
                  ❌ {error}
                </div>
              )}

              <div className="space-y-4">
                {/* Sender Account */}
                <div>
                  <label className="block text-sm font-bold mb-2 text-blue-400">
                    📤 Мои счета
                  </label>
                  <select
                    value={senderAccount ? JSON.stringify(senderAccount) : ''}
                    onChange={(e) => {
                      if (e.target.value) {
                        setSenderAccount(JSON.parse(e.target.value));
                      } else {
                        setSenderAccount(null);
                      }
                    }}
                    className="w-full px-4 py-2 bg-slate-700 border border-gray-600 rounded text-white"
                  >
                    <option value="">-- Выберите счет --</option>
                    {userAccounts.map(account => (
                      <option key={account.id} value={JSON.stringify(account)}>
                        {account.account_number} - {account.balance} {account.currency}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Receiver */}
                <div>
                  <label className="block text-sm font-bold mb-2 text-blue-400">
                    📥 Получатель
                  </label>
                  <select
                    value={receiverUser || ''}
                    onChange={(e) => setReceiverUser(parseInt(e.target.value) || null)}
                    className="w-full px-4 py-2 bg-slate-700 border border-gray-600 rounded text-white"
                  >
                    <option value="">-- Выберите получателя --</option>
                    {allUsers.map(user => (
                      <option key={user.id} value={user.id}>
                        {user.name} ({user.country})
                      </option>
                    ))}
                  </select>
                  {allUsers.length === 0 && (
                    <p className="text-xs text-gray-400 mt-1">
                      💡 Других пользователей нет. Пригласи друзей, чтобы они зарегистрировались!
                    </p>
                  )}
                </div>

                {/* Amount */}
                <div>
                  <label className="block text-sm font-bold mb-2 text-blue-400">
                    💰 Сумма ({senderAccount?.currency || 'USD'})
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    placeholder="Введите сумму"
                    className="w-full px-4 py-2 bg-slate-700 border border-gray-600 rounded text-white"
                  />
                </div>

                {/* Description */}
                <div>
                  <label className="block text-sm font-bold mb-2 text-blue-400">
                    📝 Описание
                  </label>
                  <input
                    type="text"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Описание перевода"
                    className="w-full px-4 py-2 bg-slate-700 border border-gray-600 rounded text-white"
                  />
                </div>

                {/* Fraud Settings */}
                {fraudMode && (
                  <div className="bg-red-900 bg-opacity-30 border border-red-600 rounded-lg p-4 space-y-3">
                    <h3 className="font-bold text-red-400 mb-3">⚙️ Fraud паттерны</h3>

                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={vpnFlag}
                        onChange={(e) => setVpnFlag(e.target.checked)}
                        className="w-4 h-4"
                      />
                      <span>☑ VPN/TOR флаг</span>
                    </label>

                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={geoMismatch}
                        onChange={(e) => setGeoMismatch(e.target.checked)}
                        className="w-4 h-4"
                      />
                      <span>☑ Геолокация не совпадает</span>
                    </label>

                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={nightTime}
                        onChange={(e) => setNightTime(e.target.checked)}
                        className="w-4 h-4"
                      />
                      <span>☑ Ночное время (03:00)</span>
                    </label>

                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={structuring}
                        onChange={(e) => setStructuring(e.target.checked)}
                        className="w-4 h-4"
                      />
                      <span>☑ Дробление суммы (structuring)</span>
                    </label>

                    <div className="border-t border-red-600 pt-3">
                      <label className="flex items-center gap-3 cursor-pointer mb-3">
                        <input
                          type="checkbox"
                          checked={velocityAttack}
                          onChange={(e) => setVelocityAttack(e.target.checked)}
                          className="w-4 h-4"
                        />
                        <span>☑ Velocity атака</span>
                      </label>

                      {velocityAttack && (
                        <div className="ml-7 space-y-2 text-sm">
                          <div>
                            <label className="block text-gray-300 mb-1">
                              Количество транзакций:
                              <input
                                type="number"
                                min="2"
                                max="20"
                                value={velocityCount}
                                onChange={(e) => setVelocityCount(parseInt(e.target.value) || 5)}
                                className="ml-2 w-16 px-2 py-1 bg-slate-700 border border-gray-600 rounded text-white"
                              />
                            </label>
                          </div>
                          <div>
                            <label className="block text-gray-300">
                              За (секунд):
                              <input
                                type="number"
                                min="5"
                                max="120"
                                value={velocitySeconds}
                                onChange={(e) => setVelocitySeconds(parseInt(e.target.value) || 30)}
                                className="ml-2 w-16 px-2 py-1 bg-slate-700 border border-gray-600 rounded text-white"
                              />
                            </label>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Send Button */}
                <button
                  onClick={handleSendTransfer}
                  disabled={loading || !senderAccount || !receiverUser || !amount}
                  className={`w-full px-6 py-3 rounded-lg font-bold transition disabled:cursor-not-allowed ${
                    fraudMode
                      ? 'bg-red-600 hover:bg-red-700 disabled:bg-gray-600'
                      : 'bg-green-600 hover:bg-green-700 disabled:bg-gray-600'
                  }`}
                >
                  {velocityProgress
                    ? `🚀 Отправлено ${velocityProgress.current} из ${velocityProgress.total}`
                    : loading
                    ? '⏳ Обработка...'
                    : fraudMode
                    ? '🚨 Отправить fraud'
                    : '🚀 Отправить перевод'}
                </button>
              </div>
            </div>
          </div>

          {/* Result Panel - Right Side */}
          <div className="space-y-6">
            {/* Last Transaction Result */}
            {transactionResult && (
              <div className={`rounded-lg p-6 border-2 ${getStatusColor(transactionResult.status).bg} ${getStatusColor(transactionResult.status).border}`}>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-xl font-bold">
                    {getStatusColor(transactionResult.status).icon} Результат
                  </h3>
                  <button
                    onClick={() => setTransactionResult(null)}
                    className="text-gray-400 hover:text-white"
                  >
                    ✕
                  </button>
                </div>

                <div className="space-y-3 text-sm">
                  <div>
                    <p className="text-gray-300">Статус:</p>
                    <p className={`text-lg font-bold ${getStatusColor(transactionResult.status).text}`}>
                      {transactionResult.status === 'approved' && 'ОДОБРЕНО ✅'}
                      {transactionResult.status === 'review' && 'НА ПРОВЕРКУ ⚠️'}
                      {transactionResult.status === 'blocked' && 'ЗАБЛОКИРОВАНО ❌'}
                    </p>
                  </div>

                  <div>
                    <p className="text-gray-300">Fraud Score:</p>
                    <div className="w-full bg-slate-700 rounded-full h-3 overflow-hidden mt-1">
                      <div
                        className={`h-full transition-all ${getFraudScoreColor(transactionResult.fraud_score)}`}
                        style={{ width: `${transactionResult.fraud_score * 100}%` }}
                      />
                    </div>
                    <p className="text-right text-xs mt-1 font-mono">
                      {(transactionResult.fraud_score * 100).toFixed(1)}%
                    </p>
                  </div>

                  <div>
                    <p className="text-gray-300">Объяснение:</p>
                    <p className="text-gray-200 text-xs leading-relaxed mt-1">
                      {transactionResult.explanation}
                    </p>
                  </div>

                  <div className="border-t border-gray-600 pt-3 text-xs text-gray-400">
                    <p>💳 {transactionResult.sender} → {transactionResult.receiver}</p>
                    <p>💰 {transactionResult.amount} {transactionResult.currency}</p>
                    <p>⏱️ {transactionResult.timestamp}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Transaction History */}
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <h3 className="font-bold mb-4">📋 Последние 5 транзакций</h3>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {transactions.length === 0 ? (
                  <p className="text-gray-400 text-sm text-center py-4">
                    Еще нет транзакций
                  </p>
                ) : (
                  transactions.map((txn, idx) => {
                    const statusColor = getStatusColor(txn.status);
                    return (
                      <div
                        key={idx}
                        className={`p-3 rounded border-l-4 bg-slate-700 ${statusColor.border} cursor-pointer hover:bg-slate-600 transition`}
                      >
                        <div className="flex justify-between items-start mb-1">
                          <span className="font-bold text-sm">
                            {statusColor.icon} {txn.sender} → {txn.receiver}
                          </span>
                          <span className="text-xs font-mono text-gray-400">{txn.timestamp}</span>
                        </div>
                        <div className="flex justify-between items-end">
                          <span className="text-xs text-gray-300">
                            {txn.amount} {txn.currency}
                          </span>
                          <div className="w-16 bg-slate-900 rounded-full h-2 overflow-hidden">
                            <div
                              className={`h-full ${getFraudScoreColor(txn.fraud_score)}`}
                              style={{ width: `${txn.fraud_score * 100}%` }}
                            />
                          </div>
                          <span className="text-xs font-mono text-gray-300 ml-2">
                            {(txn.fraud_score * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-black bg-opacity-50 border-t border-gray-700 mt-12">
        <div className="max-w-7xl mx-auto px-6 py-6 text-center text-gray-400 text-sm">
          <p>
            Клиент © 2026 | Подключено к: {process.env.REACT_APP_API_URL || 'http://localhost:8000'}
          </p>
        </div>
      </footer>
    </div>
  );
}

export default ClientApp;
