import { useState } from 'react';
import { useVaultStore } from '../../store/vaultStore';
import { LockClosedIcon } from '@heroicons/react/24/outline';

export function VaultUnlock() {
  const [passphrase, setPassphrase] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const { unlock, error, clearError } = useVaultStore();

  const handleUnlock = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await unlock(passphrase);
    } catch {
      // error handled by store
    }
    setSubmitting(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8">
        <div className="text-center mb-6">
          <LockClosedIcon className="w-12 h-12 text-gray-400 mx-auto mb-3" />
          <h2 className="text-2xl font-bold text-gray-900">Unlock Vault</h2>
          <p className="text-gray-500 mt-2">Enter your passphrase to access your applications.</p>
        </div>

        {error && (
          <div className="bg-red-50 text-red-700 text-sm rounded-lg p-3 mb-4">
            {error}
            <button onClick={clearError} className="ml-2 underline">dismiss</button>
          </div>
        )}

        <form onSubmit={handleUnlock} className="space-y-4">
          <div>
            <input
              type="password"
              value={passphrase}
              onChange={(e) => setPassphrase(e.target.value)}
              placeholder="Enter your passphrase"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              autoFocus
              required
            />
          </div>

          <button
            type="submit"
            disabled={submitting || !passphrase}
            className="w-full py-2 px-4 bg-blue-600 text-white rounded-lg font-medium disabled:bg-gray-300 disabled:cursor-not-allowed hover:bg-blue-700"
          >
            {submitting ? 'Unlocking...' : 'Unlock'}
          </button>
        </form>
      </div>
    </div>
  );
}
