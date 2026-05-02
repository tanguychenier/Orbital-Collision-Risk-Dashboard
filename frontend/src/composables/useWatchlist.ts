/**
 * Persistent satellite watchlist.
 *
 * The watchlist is a small set of NORAD catalog ids the user wants the
 * dashboard to highlight. It is stored in `localStorage` (no account,
 * no backend) so the experience is private and survives page reloads.
 *
 * The composable returns reactive primitives shared across consumers
 * by reusing the same module-level `Set`, so toggling the watchlist
 * on the satellite detail page is reflected on the dashboard table
 * immediately without a global store.
 */
import { computed, readonly, ref } from 'vue';

const STORAGE_KEY = 'oc:watchlist:v1';

function loadFromStorage(): number[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw === null) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((value): value is number => Number.isInteger(value));
  } catch {
    return [];
  }
}

function saveToStorage(ids: ReadonlySet<number>): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify([...ids].sort((a, b) => a - b)));
  } catch {
    /* quota exceeded or storage disabled: degrade silently */
  }
}

const watched = ref<Set<number>>(new Set(loadFromStorage()));

function persist(): void {
  saveToStorage(watched.value);
}

export function useWatchlist() {
  function isWatched(noradId: number): boolean {
    return watched.value.has(noradId);
  }

  function watch(noradId: number): void {
    if (!Number.isInteger(noradId)) return;
    if (watched.value.has(noradId)) return;
    const next = new Set(watched.value);
    next.add(noradId);
    watched.value = next;
    persist();
  }

  function unwatch(noradId: number): void {
    if (!watched.value.has(noradId)) return;
    const next = new Set(watched.value);
    next.delete(noradId);
    watched.value = next;
    persist();
  }

  function toggle(noradId: number): boolean {
    if (watched.value.has(noradId)) {
      unwatch(noradId);
      return false;
    }
    watch(noradId);
    return true;
  }

  function clear(): void {
    if (watched.value.size === 0) return;
    watched.value = new Set();
    persist();
  }

  const ids = computed<readonly number[]>(() =>
    [...watched.value].sort((a, b) => a - b)
  );
  const count = computed<number>(() => watched.value.size);

  return {
    ids,
    count,
    watched: readonly(watched),
    isWatched,
    watch,
    unwatch,
    toggle,
    clear
  };
}

/** Test-only escape hatch to reset the in-memory state between specs. */
export function __resetWatchlistForTests(): void {
  watched.value = new Set();
}
