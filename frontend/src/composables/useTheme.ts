import { storeToRefs } from 'pinia';
import { useThemeStore } from '@/stores/theme';

export function useTheme() {
  const store = useThemeStore();
  const { mode, isDark } = storeToRefs(store);
  return {
    mode,
    isDark,
    toggle: () => store.toggle(),
    setMode: store.setMode,
    initialize: () => store.initialize()
  };
}
