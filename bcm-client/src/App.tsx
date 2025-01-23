import React, { useState, useEffect } from 'react';
import { AppProvider } from './contexts/AppContext';
import { useApp } from './contexts/AppContext';
import { ApiClient } from './api/client';
import { CapabilityTree } from './components/CapabilityTree';
import { Visualize } from './components/Visualize';
import AuditLogs from './components/AuditLogs';
import { Toaster } from 'react-hot-toast';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import BurgerMenu from './components/BurgerMenu';
import About from './components/About';
import SettingsComponent from './components/Settings';
import Admin from './components/Admin';

const LoginScreen: React.FC = () => {
  const { login } = useApp();
  const [nickname, setNickname] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await login(nickname);
    } catch (error) {
      console.error('Login error:', error);
      setError('Failed to login. Please try again.');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full p-6 bg-white rounded-lg shadow-md">
        <h1 className="text-2xl font-bold text-center text-gray-900 mb-6">
          Business Capability Model
        </h1>
        {error && (
          <div className="mb-4 p-3 bg-red-100 text-red-700 rounded-md">
            {error}
          </div>
        )}
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nickname
            </label>
            <input
              type="text"
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              required
              minLength={1}
              maxLength={50}
            />
          </div>
          <button
            type="submit"
            className="w-full py-2 px-4 bg-blue-500 text-white rounded-md hover:bg-blue-600"
          >
            Enter
          </button>
        </form>
      </div>
    </div>
  );
};

const MainApp: React.FC = () => {
  const { userSession, logout, activeUsers } = useApp();

  if (!userSession) {
    return <LoginScreen />;
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/visualize/:id"
          element={
            userSession ? (
              <Visualize />
            ) : (
              <Navigate to="/" replace />
            )
          }
        />
        <Route
          path="/"
          element={
            <div className="min-h-screen bg-gray-50">
              <BurgerMenu />
              <header className="bg-white shadow">
                <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
                  <div className="flex justify-end items-center">
                    <div className="flex items-center space-x-4">
                      <div className="text-sm text-gray-600">
                        Active users: {activeUsers.length}
                      </div>
                      <div className="text-sm text-gray-600">
                        Logged in as: {userSession.nickname}
                      </div>
                      <button
                        onClick={() => ApiClient.clearLocks(userSession.session_id)}
                        className="px-3 py-2 text-sm bg-yellow-500 text-white rounded-md hover:bg-yellow-600"
                      >
                        Clear Locks
                      </button>
                      <button
                        onClick={logout}
                        className="px-3 py-2 text-sm bg-red-500 text-white rounded-md hover:bg-red-600"
                      >
                        Logout
                      </button>
                    </div>
                  </div>
                </div>
              </header>
              <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <CapabilityTree />
              </main>
            </div>
          }
        />
        <Route
          path="/about"
          element={
            <div className="min-h-screen bg-gray-50">
              <BurgerMenu />
              <header className="bg-white shadow">
                <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
                  <div className="flex justify-end items-center">
                    <div className="flex items-center space-x-4">
                      <div className="text-sm text-gray-600">
                        Active users: {activeUsers.length}
                      </div>
                      <div className="text-sm text-gray-600">
                        Logged in as: {userSession.nickname}
                      </div>
                      <button
                        onClick={() => ApiClient.clearLocks(userSession.session_id)}
                        className="px-3 py-2 text-sm bg-yellow-500 text-white rounded-md hover:bg-yellow-600"
                      >
                        Clear Locks
                      </button>
                      <button
                        onClick={logout}
                        className="px-3 py-2 text-sm bg-red-500 text-white rounded-md hover:bg-red-600"
                      >
                        Logout
                      </button>
                    </div>
                  </div>
                </div>
              </header>
              <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <About />
              </main>
            </div>
          }
        />
        <Route
          path="/settings"
          element={
            <div className="min-h-screen bg-gray-50">
              <BurgerMenu />
              <header className="bg-white shadow">
                <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
                  <div className="flex justify-end items-center">
                    <div className="flex items-center space-x-4">
                      <div className="text-sm text-gray-600">
                        Active users: {activeUsers.length}
                      </div>
                      <div className="text-sm text-gray-600">
                        Logged in as: {userSession.nickname}
                      </div>
                      <button
                        onClick={() => ApiClient.clearLocks(userSession.session_id)}
                        className="px-3 py-2 text-sm bg-yellow-500 text-white rounded-md hover:bg-yellow-600"
                      >
                        Clear Locks
                      </button>
                      <button
                        onClick={logout}
                        className="px-3 py-2 text-sm bg-red-500 text-white rounded-md hover:bg-red-600"
                      >
                        Logout
                      </button>
                    </div>
                  </div>
                </div>
              </header>
              <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <SettingsComponent />
              </main>
            </div>
          }
        />
        <Route
          path="/audit-logs"
          element={
            <div className="min-h-screen bg-gray-50">
              <BurgerMenu />
              <header className="bg-white shadow">
                <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
                  <div className="flex justify-between items-center">
                    <div className="flex items-center space-x-4 ml-auto">
                      <div className="text-sm text-gray-600">
                        Active users: {activeUsers.length}
                      </div>
                      <div className="text-sm text-gray-600">
                        Logged in as: {userSession.nickname}
                      </div>
                      <button
                        onClick={() => ApiClient.clearLocks(userSession.session_id)}
                        className="px-3 py-2 text-sm bg-yellow-500 text-white rounded-md hover:bg-yellow-600"
                      >
                        Clear Locks
                      </button>
                      <button
                        onClick={logout}
                        className="px-3 py-2 text-sm bg-red-500 text-white rounded-md hover:bg-red-600"
                      >
                        Logout
                      </button>
                    </div>
                  </div>
                </div>
              </header>
              <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <AuditLogs />
              </main>
            </div>
          }
        />
        <Route
          path="/admin"
          element={
            <div className="min-h-screen bg-gray-50">
              <BurgerMenu />
              <header className="bg-white shadow">
                <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
                  <div className="flex justify-between items-center">
                    <div className="flex items-center space-x-4 ml-auto">
                      <div className="text-sm text-gray-600">
                        Active users: {activeUsers.length}
                      </div>
                      <div className="text-sm text-gray-600">
                        Logged in as: {userSession.nickname}
                      </div>
                      <button
                        onClick={() => ApiClient.clearLocks(userSession.session_id)}
                        className="px-3 py-2 text-sm bg-yellow-500 text-white rounded-md hover:bg-yellow-600"
                      >
                        Clear Locks
                      </button>
                      <button
                        onClick={logout}
                        className="px-3 py-2 text-sm bg-red-500 text-white rounded-md hover:bg-red-600"
                      >
                        Logout
                      </button>
                    </div>
                  </div>
                </div>
              </header>
              <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <Admin />
              </main>
            </div>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
};

const App: React.FC = () => {
  useEffect(() => {
    const requestClipboardPermission = async () => {
      try {
        const result = await navigator.permissions.query({ name: 'clipboard-read' as PermissionName });
        if (result.state === 'prompt') {
          // This will trigger the permission prompt
          await navigator.clipboard.readText().catch(() => {
            // Ignore error if user denies permission
          });
        }
      } catch (error) {
        console.warn('Clipboard permission request failed:', error);
      }
    };

    requestClipboardPermission();
  }, []);

  return (
    <AppProvider>
      <MainApp />
      <Toaster />
    </AppProvider>
  );
};

export default App;
