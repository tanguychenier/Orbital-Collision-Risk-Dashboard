<script setup lang="ts">
import { onMounted } from 'vue';
import { RouterView } from 'vue-router';
import { useThemeStore } from '@/stores/theme';
import Toast from 'primevue/toast';

const theme = useThemeStore();

onMounted(() => {
  theme.initialize();
});
</script>

<template>
  <div class="min-h-full flex flex-col">
    <RouterView />
    <Toast position="bottom-right" />
  </div>
</template>
