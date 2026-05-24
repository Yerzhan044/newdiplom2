import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

function LoginPage() {
  const navigate = useNavigate();
  const { login, register, isAuthenticated } = useAuth();

  const [mode, setMode] = useState('login'); // 'login' or 'register'
  const [username, setUsername] = useState('');
  const [country, setCountry] = useState('KZ');
  const [bank, setBank] = useState('Demo Bank');
  const [initialBalance, setInitialBalance] = useState('100000');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/client');
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setLoading(true);

    try {
      let result;

      if (mode === 'login') {
        result = await login(username);
      } else {
        result = await register(username, country, bank, parseFloat(initialBalance));
      }

      if (result.success) {
        setSuccess(result.message);
        setUsername('');
        // Wait a bit then redirect
        setTimeout(() => {
          navigate('/client');
        }, 1000);
      } else {
        setError(result.message);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white flex items-center justify-center p-4">
      {/* Main Container */}
      <div className="w-full max-w-md space-y-8">
        {/* Header */}
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold">🛡️ Fraud Detection</h1>
          <p className="text-gray-400">Демонстрационная система для друзей</p>
        </div>

        {/* Auth Form */}
        <div className="bg-slate-800 rounded-lg p-8 border border-blue-500 space-y-6">
          {/* Mode Toggle */}
          <div className="flex gap-2 bg-slate-700 p-1 rounded-lg">
            <button
              onClick={() => setMode('login')}
              className={`flex-1 py-2 px-4 rounded font-bold transition ${
                mode === 'login'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              Вход
            </button>
            <button
              onClick={() => setMode('register')}
              className={`flex-1 py-2 px-4 rounded font-bold transition ${
                mode === 'register'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              Регистрация
            </button>
          </div>

          {/* Messages */}
          {error && (
            <div className="bg-red-900 border border-red-700 p-4 rounded text-red-200 text-sm">
              ❌ {error}
            </div>
          )}

          {success && (
            <div className="bg-green-900 border border-green-700 p-4 rounded text-green-200 text-sm">
              ✅ {success}
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Username */}
            <div>
              <label className="block text-sm font-bold mb-2 text-blue-400">
                👤 {mode === 'login' ? 'Имя пользователя' : 'Выбери имя'}
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder={mode === 'login' ? 'Alice' : 'Введи своё имя'}
                className="w-full px-4 py-2 bg-slate-700 border border-gray-600 rounded text-white placeholder-gray-500"
                required
              />
              {mode === 'register' && (
                <p className="text-xs text-gray-400 mt-1">
                  💡 Используется как имя аккаунта для других пользователей
                </p>
              )}
            </div>

            {/* Registration fields */}
            {mode === 'register' && (
              <>
                {/* Country */}
                <div>
                  <label className="block text-sm font-bold mb-2 text-blue-400">
                    🌍 Страна
                  </label>
                  <select
                    value={country}
                    onChange={(e) => setCountry(e.target.value)}
                    className="w-full px-4 py-2 bg-slate-700 border border-gray-600 rounded text-white"
                  >
                    <option value="KZ">Kazakhstan (KZ)</option>
                    <option value="RU">Russia (RU)</option>
                    <option value="US">United States (US)</option>
                    <option value="DE">Germany (DE)</option>
                    <option value="GB">United Kingdom (GB)</option>
                    <option value="FR">France (FR)</option>
                  </select>
                </div>

                {/* Bank */}
                <div>
                  <label className="block text-sm font-bold mb-2 text-blue-400">
                    🏦 Банк
                  </label>
                  <input
                    type="text"
                    value={bank}
                    onChange={(e) => setBank(e.target.value)}
                    placeholder="Demo Bank"
                    className="w-full px-4 py-2 bg-slate-700 border border-gray-600 rounded text-white"
                  />
                </div>

                {/* Initial Balance */}
                <div>
                  <label className="block text-sm font-bold mb-2 text-blue-400">
                    💰 Начальный баланс (USD)
                  </label>
                  <input
                    type="number"
                    value={initialBalance}
                    onChange={(e) => setInitialBalance(e.target.value)}
                    placeholder="100000"
                    className="w-full px-4 py-2 bg-slate-700 border border-gray-600 rounded text-white"
                  />
                  <p className="text-xs text-gray-400 mt-1">
                    💡 По 3 счета будут созданы в USD, EUR, KZT с этим балансом
                  </p>
                </div>
              </>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading || !username}
              className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded font-bold transition mt-6"
            >
              {loading
                ? mode === 'login'
                  ? '⏳ Вход...'
                  : '⏳ Регистрация...'
                : mode === 'login'
                ? '🔓 Войти'
                : '✨ Создать аккаунт'}
            </button>
          </form>

          {/* Info */}
          <div className="bg-slate-700 p-4 rounded border border-slate-600 text-sm text-gray-300 space-y-2">
            <p>
              <strong>ℹ️ Без пароля!</strong> Просто введи имя для входа или регистрации.
            </p>
            <p>
              <strong>🎁 Новые пользователи:</strong> Получат 3 счета (USD, EUR, KZT) с начальным балансом.
            </p>
            <p>
              <strong>👥 Пригласи друзей:</strong> Они могут зарегистрироваться и отправлять переводы друг другу!
            </p>
          </div>
        </div>

        {/* Demo Info */}
        <div className="text-center space-y-2 text-sm text-gray-400">
          <p>📱 Версия: 1.0</p>
          <p>🔗 API: {process.env.REACT_APP_API_URL || 'http://localhost:8000'}</p>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;
