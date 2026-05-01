import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

export type ViewportSize = 'mobile' | 'tablet' | 'desktop';

export function useViewport() {
  const width = ref(typeof window === 'undefined' ? 1920 : window.innerWidth);
  const height = ref(typeof window === 'undefined' ? 1080 : window.innerHeight);

  const update = () => {
    width.value = window.innerWidth;
    height.value = window.innerHeight;
  };

  onMounted(() => {
    update();
    window.addEventListener('resize', update, { passive: true });
  });

  onBeforeUnmount(() => {
    window.removeEventListener('resize', update);
  });

  const size = computed<ViewportSize>(() => {
    if (width.value < 640) return 'mobile';
    if (width.value < 1024) return 'tablet';
    return 'desktop';
  });

  const isMobile = computed(() => size.value === 'mobile');
  const isTablet = computed(() => size.value === 'tablet');
  const isDesktop = computed(() => size.value === 'desktop');

  return { width, height, size, isMobile, isTablet, isDesktop };
}
