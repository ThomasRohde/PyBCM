import { useApp } from '../contexts/AppContext';
import { ApiClient } from '../api/client';
import BackButton from './BackButton';

export default function Admin() {
  const { userSession } = useApp();

  const handleReset = async () => {
    if (!userSession) {
      alert('You must be logged in to perform this action');
      return;
    }

    if (window.confirm('Are you sure you want to reset the database? This action cannot be undone.')) {
      try {
        await ApiClient.resetDatabase(userSession.session_id);
        alert('Database reset successfully');
      } catch (error) {
        console.error('Failed to reset database:', error);
        alert('Failed to reset database');
      }
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <BackButton />

      <h1 className="text-3xl font-bold mb-8">Admin</h1>
      
      <section className="mb-8">
        <h2 className="text-2xl font-semibold mb-4">Database Management</h2>
        <div className="space-y-4">
          <button
            onClick={handleReset}
            className="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline"
          >
            Reset Database
          </button>
          <p className="text-gray-600 text-sm mt-2">
            Warning: This will reset the database to its initial state and clear all capabilities.
          </p>
        </div>
      </section>
    </div>
  );
}
