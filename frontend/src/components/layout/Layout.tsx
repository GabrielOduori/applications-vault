import { useEffect, useState, type ReactNode } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  HomeIcon,
  BriefcaseIcon,
  MagnifyingGlassIcon,
  LockClosedIcon,
  Cog6ToothIcon,
} from '@heroicons/react/24/outline';
import { useVaultStore } from '../../store/vaultStore';
import { Modal } from '../common/Modal';
import { api } from '../../api/client';

const NAV_ITEMS = [
  { path: '/', label: 'Dashboard', icon: HomeIcon },
  { path: '/jobs', label: 'Jobs', icon: BriefcaseIcon },
  { path: '/search', label: 'Search', icon: MagnifyingGlassIcon },
];

export function Layout({ children }: { children: ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();
  const lock = useVaultStore((s) => s.lock);
  const [showSettings, setShowSettings] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === 'k') {
        e.preventDefault();
        navigate('/search');
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [navigate]);

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <h1 className="text-xl font-bold text-gray-900">Application Vault</h1>
              </div>
              <div className="hidden sm:ml-8 sm:flex sm:space-x-4">
                {NAV_ITEMS.map((item) => {
                  const active = location.pathname === item.path;
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      className={`inline-flex items-center px-3 py-2 text-sm font-medium rounded-md ${
                        active
                          ? 'bg-gray-100 text-gray-900'
                          : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                      }`}
                    >
                      <item.icon className="w-4 h-4 mr-2" />
                      {item.label}
                    </Link>
                  );
                })}
              </div>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setShowSettings(true)}
                className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-700 hover:bg-gray-50 rounded-md"
                title="Vault settings"
              >
                <Cog6ToothIcon className="w-4 h-4" />
              </button>
              <button
                onClick={lock}
                className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-md"
              >
                <LockClosedIcon className="w-4 h-4 mr-1" />
                Lock
              </button>
            </div>
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {children}
      </main>

      <VaultSettingsModal open={showSettings} onClose={() => setShowSettings(false)} />
    </div>
  );
}

function VaultSettingsModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [minutes, setMinutes] = useState(15);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');

  const handleSave = async () => {
    setSaving(true);
    setError('');
    setSaved(false);
    try {
      await api.updateVaultSettings(minutes * 60);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to save settings');
    }
    setSaving(false);
  };

  return (
    <Modal open={open} onClose={onClose} title="Vault Settings">
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Auto-lock timeout (minutes)
          </label>
          <input
            type="number"
            min={1}
            max={480}
            value={minutes}
            onChange={(e) => setMinutes(Math.max(1, Number(e.target.value)))}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          <p className="mt-1 text-xs text-gray-400">
            Vault will lock automatically after this many minutes of inactivity.
          </p>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          onClick={handleSave}
          disabled={saving}
          className="w-full py-2 px-4 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:bg-gray-300"
        >
          {saving ? 'Saving…' : saved ? 'Saved!' : 'Save Settings'}
        </button>
      </div>
    </Modal>
  );
}
