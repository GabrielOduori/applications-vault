import { useState } from 'react';
import { useVaultStore } from '../../store/vaultStore';
import { ShieldCheckIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';

export function VaultSetup() {
  const [passphrase, setPassphrase] = useState('');
  const [confirm, setConfirm] = useState('');
  const [recoveryKey, setRecoveryKey] = useState<string | null>(null);
  const [acknowledged, setAcknowledged] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const { setup, unlock, error, clearError } = useVaultStore();

  const handleSetup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (passphrase !== confirm) return;
    if (passphrase.length < 8) return;

    setSubmitting(true);
    try {
      const key = await setup(passphrase);
      setRecoveryKey(key);
    } catch {
      // error handled by store
    }
    setSubmitting(false);
  };

  const handleContinue = async () => {
    await unlock(passphrase);
  };

  if (recoveryKey) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
        <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8">
          <div className="text-center mb-6">
            <ShieldCheckIcon className="w-12 h-12 text-green-500 mx-auto mb-3" />
            <h2 className="text-2xl font-bold text-gray-900">Vault Created</h2>
          </div>

          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
            <div className="flex items-start">
              <ExclamationTriangleIcon className="w-5 h-5 text-yellow-600 mt-0.5 mr-2 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-yellow-800">Save your recovery key</p>
                <p className="text-xs text-yellow-700 mt-1">
                  This is the only time it will be shown. If you lose both your passphrase and recovery key, your vault cannot be recovered.
                </p>
              </div>
            </div>
          </div>

          <div className="bg-gray-100 rounded-lg p-3 mb-6">
            <code className="text-sm text-gray-800 break-all select-all">{recoveryKey}</code>
          </div>

          <label className="flex items-start gap-2 mb-6 cursor-pointer">
            <input
              type="checkbox"
              checked={acknowledged}
              onChange={(e) => setAcknowledged(e.target.checked)}
              className="mt-1"
            />
            <span className="text-sm text-gray-600">
              I have saved my recovery key and understand that if I lose it along with my passphrase, my vault data will be permanently inaccessible.
            </span>
          </label>

          <button
            onClick={handleContinue}
            disabled={!acknowledged}
            className="w-full py-2 px-4 bg-blue-600 text-white rounded-lg font-medium disabled:bg-gray-300 disabled:cursor-not-allowed hover:bg-blue-700"
          >
            Continue to Vault
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8">
        <div className="text-center mb-6">
          <ShieldCheckIcon className="w-12 h-12 text-blue-500 mx-auto mb-3" />
          <h2 className="text-2xl font-bold text-gray-900">Create Your Vault</h2>
          <p className="text-gray-500 mt-2">Set up a secure passphrase to protect your application data.</p>
        </div>

        {error && (
          <div className="bg-red-50 text-red-700 text-sm rounded-lg p-3 mb-4">
            {error}
            <button onClick={clearError} className="ml-2 underline">dismiss</button>
          </div>
        )}

        <form onSubmit={handleSetup} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Passphrase</label>
            <input
              type="password"
              value={passphrase}
              onChange={(e) => setPassphrase(e.target.value)}
              placeholder="At least 8 characters"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              minLength={8}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Confirm Passphrase</label>
            <input
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder="Type it again"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              required
            />
            {confirm && passphrase !== confirm && (
              <p className="text-red-500 text-xs mt-1">Passphrases don't match</p>
            )}
          </div>

          <button
            type="submit"
            disabled={submitting || passphrase.length < 8 || passphrase !== confirm}
            className="w-full py-2 px-4 bg-blue-600 text-white rounded-lg font-medium disabled:bg-gray-300 disabled:cursor-not-allowed hover:bg-blue-700"
          >
            {submitting ? 'Creating vault...' : 'Create Vault'}
          </button>
        </form>
      </div>
    </div>
  );
}
