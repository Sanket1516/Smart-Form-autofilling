import { defineConfig } from 'vite';
import { resolve } from 'path';

// Content script: one self-contained classic script (no imports, no chunks).
export default defineConfig({
  build: {
    outDir: 'dist',
    emptyOutDir: false,
    lib: {
      entry: resolve(__dirname, 'src/content/index.ts'),
      name: 'SmartFormContent',
      formats: ['iife'],
      fileName: () => 'content.js',
    },
  },
});
