import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { title: 'Dashboard' }
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
