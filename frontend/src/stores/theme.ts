import { defineStore } from 'pinia';

export type ThemeMode = 'dark' | 'light';

const STORAGE_KEY = 'oc:theme';

function applyTheme(mode: ThemeMode) {
  if (typeof document === 'undefined') return;
  const root = document.documentElement;
  if (mode === 'dark') {
    root.classList.add('app-dark');
    root.classList.remove('light');
  } else {
    root.classList.remove('app-dark');
    root.classList.add('light');
  }
}

function detectInitial(): ThemeMode {
  if (typeof window === 'undefined') return 'dark';
  const stored = window.localStorage?.getItem(STORAGE_KEY) as ThemeMode | null;
  if (stored === 'dark' || stored === 'light') return stored;
  if (window.matchMedia?.('(prefers-color-scheme: light)').matches) return 'light';
  return 'dark';
}

export const useThemeStore = defineStore('theme', {
  state: () => ({
    mode: 'dark' as ThemeMode,
    initialized: false
  }),
  getters: {
    isDark: (state) => state.mode === 'dark'
  },
  actions: {
    initialize() {
      if (this.initialized) return;
      this.mode = detectInitial();
      applyTheme(this.mode);
      this.initialized = true;
    },
    setMode(mode: ThemeMode) {
      this.mode = mode;
      applyTheme(mode);
      try {
        window.localStorage?.setItem(STORAGE_KEY, mode);
      } catch {
        /* ignore */
      }
    },
    toggle() {
      this.setMode(this.mode === 'dark' ? 'light' : 'dark');
    }
  }
});
