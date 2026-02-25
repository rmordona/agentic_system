// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: ui_platform/frontend/vite.config.ts
//
// Description:
//   Vite configuration for the Agentic System frontend. Sets up React plugin,
//   path aliases, TypeScript support, and production optimizations.
//
// Author: Raymond M.O. Ordona
// Created: 2026-01-04
// -----------------------------------------------------------------------------

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// -----------------------------------------------------------------------------
// Vite Configuration
// -----------------------------------------------------------------------------
export default defineConfig({
  plugins: [
    // React plugin: Enables fast refresh, JSX transformation, and TS support
    react(),
  ],
  resolve: {
    alias: {
      // Aliases for cleaner imports
      '@': path.resolve(__dirname, 'src'),
      '@app': path.resolve(__dirname, 'src/app'),
      '@api': path.resolve(__dirname, 'src/api'),
      '@components': path.resolve(__dirname, 'src/app/components'),
    },
  },
  server: {
    // Development server options
    port: 5173,          // Default Vite dev port
    open: true,          // Open browser on start
    cors: true,          // Enable CORS for backend integration
    fs: {
      strict: false,
    },
  },
  preview: {
    port: 4173,          // Preview production build
  },
  build: {
    outDir: 'dist',
    sourcemap: true,     // Generate source maps for production
    target: 'esnext',    // Modern JS target
    rollupOptions: {
      input: 'index.html', 
      output: {
        manualChunks(id) {
          // Separate vendor dependencies for better caching
          if (id.includes('node_modules')) {
            return 'vendor'
          }
        },
      },
    },
  },
  define: {
    'process.env': {},    // Avoid undefined process.env in frontend code
  },
})
