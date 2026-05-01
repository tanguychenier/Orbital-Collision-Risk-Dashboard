import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { title: 'Dashboard' }
  },
  {
    path: '/heatmap',
    name: 'heatmap',
    component: () => import('@/views/Heatmap.vue'),
    meta: { title: 'Heatmap' }
  },
  {
    path: '/satellite/:noradId',
    name: 'satellite-detail',
    component: () => import('@/views/SatelliteDetail.vue'),
    meta: { title: 'Satellite' }
  },
  {
    path: '/alerts',
    name: 'alerts',
    component: () => import('@/views/Alerts.vue'),
    meta: { title: 'Alerts' }
  }
];

export const router = createRouter({
  history: createWebHistory(),
  routes
});

router.afterEach((to) => {
  const base = 'Orbital Conjunctions';
  document.title = to.meta?.title ? `${to.meta.title} - ${base}` : base;
});
