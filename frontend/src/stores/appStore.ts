import { create } from 'zustand';
import type { RepoInfo } from '@/types';
import { fetchRepos } from '@/api/issues';

interface AppState {
  currentRepo: { owner: string; name: string };
  repos: RepoInfo[];
  setCurrentRepo: (owner: string, name: string) => void;
  loadRepos: () => Promise<void>;
}

export const useAppStore = create<AppState>((set) => ({
  currentRepo: { owner: 'matrixorigin', name: 'matrixone' },
  repos: [],
  setCurrentRepo: (owner, name) => set({ currentRepo: { owner, name } }),
  loadRepos: async () => {
    const repos = await fetchRepos();
    set({ repos });
  },
}));
