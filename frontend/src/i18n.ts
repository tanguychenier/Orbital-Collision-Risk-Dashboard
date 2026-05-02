import { createI18n } from 'vue-i18n';

const messages = {
  en: {
    app: {
      title: 'Orbital Conjunctions',
      tagline: 'Real-time satellite collision risk dashboard'
    },
    nav: {
      about: 'About',
      github: 'GitHub',
      toggleTheme: 'Toggle color theme'
    },
    stats: {
      activeSatellites: 'Active satellites',
      conj24h: 'Conjunctions (next 24 h)',
      conj72h: 'Conjunctions (next 72 h)',
      highRisk: 'High-risk events (< 1 km)',
      lastUpdate: 'TLE last updated'
    },
    table: {
      title: 'Upcoming conjunctions',
      tca: 'TCA (UTC)',
      satA: 'Satellite A',
      satB: 'Satellite B',
      missDistance: 'Miss distance',
      relVelocity: 'Rel. velocity',
      probability: 'Probability',
      maxDistance: 'Max miss distance (km)',
      empty: 'No conjunctions matching the current filters.',
      view: 'View details',
      exportCsv: 'CSV',
      subscribeCalendar: 'Calendar feed',
      onlyWatched: 'Only my satellites',
      watchedSatellite: 'On your watchlist'
    },
    globe: {
      title: '3D situational view',
      show: 'Show globe',
      hide: 'Hide globe',
      loading: 'Loading orbital scene...'
    },
    detail: {
      title: 'Conjunction details',
      tabRaw: 'Raw values',
      tabExplain: 'Explain',
      close: 'Close',
      tleA: 'TLE - {name}',
      tleB: 'TLE - {name}'
    },
    footer: {
      builtBy: 'Built by',
      author: 'Tanguy Chénier',
      site: 'tansoftware.com',
      tools: 'latest tools',
      links: 'Links'
    },
    error: {
      generic: 'Something went wrong while contacting the API.'
    },
    search: {
      placeholder: 'Search a satellite...',
      empty: 'No satellite matches.'
    },
    satellite: {
      back: 'Back to dashboard',
      norad: 'NORAD ID',
      country: 'Country',
      type: 'Type',
      launchDate: 'Launch date',
      lastTleEpoch: 'Last TLE epoch',
      stats: {
        next24h: 'Conjunctions (next 24 h)',
        next72h: 'Conjunctions (next 72 h)',
        next7d: 'Conjunctions (next 7 d)'
      },
      upcoming: 'Upcoming conjunctions',
      copyPermalink: 'Copy permalink',
      permalinkCopied: 'Permalink copied to clipboard',
      notFound: 'Satellite not found.',
      loading: 'Loading satellite...',
      watch: 'Watch',
      unwatch: 'Watching',
      downloadTle: 'TLE'
    }
  }
};

export const i18n = createI18n({
  legacy: false,
  locale: 'en',
  fallbackLocale: 'en',
  messages
});
