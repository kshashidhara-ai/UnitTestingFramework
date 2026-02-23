import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// Demo build config — API served from same origin (no proxy needed)
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
  define: {
    // API base URL points to same origin in demo
    __API_BASE__: JSON.stringify('/api/v1'),
  },
})
