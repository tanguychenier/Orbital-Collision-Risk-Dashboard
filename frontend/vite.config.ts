import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import tailwindcss from '@tailwindcss/vite';
import cesium from 'vite-plugin-cesium';
import { fileURLToPath, URL } from 'node:url';

export default defineConfig({
  plugins: [vue(), tailwindcss(), cesium()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  // Pre-bundle Cesium with esbuild so its internal cyclic imports are
  // resolved BEFORE Rollup chunking kicks in. Without this, the production
  // build has a Temporal-Dead-Zone error ("Cannot access 't' before
  // initialization") inside the lazy Cesium chunk.
  optimizeDeps: {
    include: ['cesium']
  },
  server: {
    port: 5173,
    host: true
  },
  build: {
    target: 'esnext',
    sourcemap: true,
    chunkSizeWarningLimit: 4000,
    // Disable name mangling on Cesium's variables - the minifier shortens
    // identifiers across module boundaries and that's what surfaces the
    // TDZ. Letting esbuild keep names is harmless for Cesium's bundle size.
    minify: 'esbuild',
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          if (id.includes('primevue')) return 'primevue';
          if (id.includes('@tanstack')) return 'vendor-query';
          return undefined;
        }
      }
    }
  },
  esbuild: {
    keepNames: true
  }
});
