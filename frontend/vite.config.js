import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';

const backend = process.env.SINAC_BACKEND_URL || 'http://localhost:8000';

export default defineConfig({
  plugins: [react({include: /\.jsx?$/})],
  // El código fuente usa JSX dentro de archivos .js (herencia de Create React App).
  esbuild: {loader: 'jsx', include: /src\/.*\.jsx?$/, exclude: []},
  optimizeDeps: {esbuildOptions: {loader: {'.js': 'jsx'}}},
  build: {outDir: 'build', sourcemap: false},
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.js'],
    include: ['src/**/*.test.js'],
    css: false,
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {target: backend, changeOrigin: true},
      '/media': {target: backend, changeOrigin: true},
    },
  },
});
