import { useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useVaultStore } from './store/vaultStore';
import { VaultSetup } from './components/vault/VaultSetup';
import { VaultUnlock } from './components/vault/VaultUnlock';
import { Layout } from './components/layout/Layout';
import { Dashboard } from './pages/Dashboard';
import { JobListPage } from './pages/JobListPage';
import { JobDetailPage } from './pages/JobDetailPage';
import { SearchPage } from './pages/SearchPage';

export default function App() {
  const { initialized, locked, loading, checkStatus } = useVaultStore();

  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  useEffect(() => {
    const handleLocked = () => checkStatus();
    window.addEventListener('vault:locked', handleLocked);
    return () => window.removeEventListener('vault:locked', handleLocked);
  }, [checkStatus]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-500">Connecting to vault...</p>
        </div>
      </div>
    );
  }

  if (!initialized) {
    return <VaultSetup />;
  }

  if (locked) {
    return <VaultUnlock />;
  }

  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/jobs" element={<JobListPage />} />
          <Route path="/jobs/:id" element={<JobDetailPage />} />
          <Route path="/search" element={<SearchPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
