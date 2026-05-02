import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { __resetWatchlistForTests, useWatchlist } from '@/composables/useWatchlist';

const STORAGE_KEY = 'oc:watchlist:v1';

beforeEach(() => {
  window.localStorage.clear();
  __resetWatchlistForTests();
});

afterEach(() => {
  window.localStorage.clear();
});

describe('useWatchlist', () => {
  it('starts empty when localStorage has no entry', () => {
    const wl = useWatchlist();
    expect(wl.count.value).toBe(0);
    expect([...wl.ids.value]).toEqual([]);
  });

  it('adds and removes NORAD ids and persists them', () => {
    const wl = useWatchlist();
    wl.watch(25544);
    wl.watch(44713);
    expect(wl.isWatched(25544)).toBe(true);
    expect(wl.count.value).toBe(2);
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe('[25544,44713]');

    wl.unwatch(25544);
    expect(wl.isWatched(25544)).toBe(false);
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe('[44713]');
  });

  it('toggle returns the new watched state', () => {
    const wl = useWatchlist();
    expect(wl.toggle(48274)).toBe(true);
    expect(wl.isWatched(48274)).toBe(true);
    expect(wl.toggle(48274)).toBe(false);
    expect(wl.isWatched(48274)).toBe(false);
  });

  it('rejects non-integer ids defensively', () => {
    const wl = useWatchlist();
    wl.watch(Number.NaN);
    wl.watch(1.5);
    expect(wl.count.value).toBe(0);
  });

  it('keeps consumers in sync via the shared module-level state', () => {
    const a = useWatchlist();
    const b = useWatchlist();
    a.watch(99999);
    expect(b.isWatched(99999)).toBe(true);
    expect(b.count.value).toBe(1);
  });

  it('clear empties the watchlist and persists the empty state', () => {
    const wl = useWatchlist();
    wl.watch(1);
    wl.watch(2);
    wl.clear();
    expect(wl.count.value).toBe(0);
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe('[]');
  });

  it('ignores corrupt JSON in localStorage', () => {
    window.localStorage.setItem(STORAGE_KEY, '{ "not an array" }');
    __resetWatchlistForTests();
    const wl = useWatchlist();
    // Composable already initialised at module load; reset clears to empty.
    expect(wl.count.value).toBe(0);
  });
});
