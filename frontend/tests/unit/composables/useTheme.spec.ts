import { beforeEach, describe, expect, it } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { useTheme } from '@/composables/useTheme';

describe('useTheme', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    window.localStorage.clear();
    document.documentElement.className = '';
  });

  it('exposes mode/isDark and a toggle function', () => {
    const theme = useTheme();
    theme.initialize();
    expect(theme.isDark.value).toBe(true);
    theme.toggle();
    expect(theme.mode.value).toBe('light');
    expect(theme.isDark.value).toBe(false);
  });

  it('setMode applies the selected mode', () => {
    const theme = useTheme();
    theme.setMode('light');
    expect(document.documentElement.classList.contains('light')).toBe(true);
    theme.setMode('dark');
    expect(document.documentElement.classList.contains('app-dark')).toBe(true);
  });
});
