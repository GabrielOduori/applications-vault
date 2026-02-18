import { create } from 'zustand';
import { api } from '../api/client';

interface VaultState {
  initialized: boolean;
  locked: boolean;
  loading: boolean;
  error: string | null;
  checkStatus: () => Promise<void>;
  setup: (passphrase: string, vaultPath?: string) => Promise<string>;
  unlock: (passphrase: string) => Promise<void>;
  lock: () => Promise<void>;
  clearError: () => void;
}

export const useVaultStore = create<VaultState>((set) => ({
  initialized: false,
  locked: true,
  loading: true,
  error: null,

  checkStatus: async () => {
    try {
      set({ loading: true });
      const status = await api.vaultStatus();

      if (!status.initialized) {
        set({ initialized: false, locked: true, loading: false });
        return;
      }

      if (status.locked) {
        api.setToken(null);
        set({ initialized: true, locked: true, loading: false });
        return;
      }

      // Server says unlocked — verify our local token is still accepted
      if (!api.getToken()) {
        set({ initialized: true, locked: true, loading: false });
        return;
      }

      try {
        await api.getJobs({ page: 1 });
        set({ initialized: true, locked: false, loading: false });
      } catch {
        // api.getJobs throws on 401 and clears the token internally;
        // treat any failure here as the token being invalid.
        set({ initialized: true, locked: true, loading: false });
      }
    } catch {
      set({ loading: false, error: 'Cannot connect to vault service' });
    }
  },

  setup: async (passphrase: string, vaultPath?: string) => {
    try {
      set({ error: null });
      const result = await api.vaultSetup(passphrase, vaultPath);
      set({ initialized: true });
      return result.recovery_key;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Setup failed';
      set({ error: msg });
      throw e;
    }
  },

  unlock: async (passphrase: string) => {
    try {
      set({ error: null });
      const result = await api.vaultUnlock(passphrase);
      api.setToken(result.token);
      set({ locked: false });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Unlock failed';
      set({ error: msg });
      throw e;
    }
  },

  lock: async () => {
    try {
      await api.vaultLock();
    } catch {
      // Lock anyway on client side
    }
    api.setToken(null);
    set({ locked: true });
  },

  clearError: () => set({ error: null }),
}));
