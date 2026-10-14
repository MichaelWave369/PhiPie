import { defineConfig } from 'vite';

export default defineConfig({
  base: '/PhiPie/',
  esbuild: { jsx: 'automatic' },
  build: { outDir: 'dist', emptyOutDir: true, sourcemap: false },
});
