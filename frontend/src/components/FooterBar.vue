<script setup lang="ts">
const repoUrl = 'https://github.com/Tan-Software/Orbital-Collision-Risk-Dashboard';
</script>

<template>
  <footer
    class="border-t border-white/10 bg-black/40 backdrop-blur mt-6"
    role="contentinfo"
    data-testid="footer-bar"
  >
    <div
      class="mx-auto max-w-screen-2xl px-4 py-4 flex items-center justify-center gap-3 text-xs text-white/60"
    >
      <span>MIT licence</span>
      <span aria-hidden="true">·</span>
      <a
        :href="repoUrl"
        target="_blank"
        rel="noopener noreferrer"
        class="inline-flex items-center gap-1.5 hover:text-cyan-300 transition focus-ring"
        aria-label="Source on GitHub"
      >
        <i class="pi pi-github" aria-hidden="true" />
        <span>Source on GitHub</span>
      </a>
    </div>
  </footer>
</template>
