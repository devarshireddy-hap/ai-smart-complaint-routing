import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Used only for the local dev proxy below. In production the frontend calls
// VITE_API_BASE_URL directly (see src/services/api.js) — this value is never
// shipped to the browser bundle.
const BACKEND_ORIGIN = process.env.VITE_DEV_BACKEND_ORIGIN || 'http://localhost:5000';

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api/v1': { target: BACKEND_ORIGIN, changeOrigin: true, secure: false },
      '/auth': { target: BACKEND_ORIGIN, changeOrigin: true, secure: false },
    },
  },
  preview: {
    host: true,
    port: 4173,
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/setupTests.js',
    globals: true,
  },
});
