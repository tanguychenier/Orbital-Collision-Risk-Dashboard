import { beforeEach, describe, expect, it } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { useThemeStore } from '@/stores/theme';

describe('theme store', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    window.localStorage.clear();
    document.documentElement.className = '';
  });

  it('initializes with dark mode by default', () => {
    const store = useThemeStore();
    store.initialize();
    expect(store.mode).toBe('dark');
    expect(store.isDark).toBe(true);
    expect(document.documentElement.classList.contains('app-dark')).toBe(true);
  });

  it('toggle switches between light and dark and persists', () => {
    const store = useThemeStore();
    store.initialize();
    store.toggle();
    expect(store.mode).toBe('light');
    expect(window.localStorage.getItem('oc:theme')).toBe('light');
    store.toggle();
    expect(store.mode).toBe('dark');
    expect(document.documentElement.classList.contains('app-dark')).toBe(true);
  });

  it('respects stored preference on initialize', () => {
    window.localStorage.setItem('oc:theme', 'light');
    const store = useThemeStore();
    store.initialize();
    expect(store.mode).toBe('light');
    expect(document.documentElement.classList.contains('light')).toBe(true);
  });
});
