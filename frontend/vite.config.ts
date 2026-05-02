import { defineConfig, type PluginOption } from 'vite';
import vue from '@vitejs/plugin-vue';
import tailwindcss from '@tailwindcss/vite';
import cesium from 'vite-plugin-cesium';
import { fileURLToPath, URL } from 'node:url';

/**
 * Inject the Cesium UMD bundle as a `<script>` tag in dev only. In dev,
 * Vite's esbuild dep optimiser pre-bundles Cesium from its ES-source
 * tangle and the resulting JS silently fails to render the globe on
 * Firefox 130+ (Chromium masks the bug). Loading the prebuilt UMD
 * `/cesium/Cesium.js` (which `vite-plugin-cesium` already serves under
 * `/cesium/`) sidesteps the dep optimiser entirely and exposes a global
 * `window.Cesium` we can read directly. In production the same plugin
 * already injects this tag as part of its `externalGlobals` workflow,
 * so this dev-only injection avoids duplicate loads.
 */
function injectCesiumUmdInDev(): PluginOption {
  return {
    name: 'oc:inject-cesium-umd-in-dev',
    apply: 'serve',
    transformIndexHtml() {
      return [
        {
          tag: 'script',
          attrs: { src: '/cesium/Cesium.js' },
          injectTo: 'head'
        }
      ];
    }
  };
}

export default defineConfig({
  plugins: [vue(), tailwindcss(), cesium(), injectCesiumUmdInDev()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  // We no longer pre-bundle Cesium with esbuild: the prebuilt UMD
  // bundle is loaded as a `<script>` tag instead (see
  // `injectCesiumUmdInDev` above and `vite-plugin-cesium`'s prod
  // injection). Excluding it from the optimiser also keeps cold dev
  // starts much faster.
  optimizeDeps: {
    exclude: ['cesium']
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
