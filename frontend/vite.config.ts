/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    // Enable globals so you don't need to import describe, it, expect, etc.
    globals: true,
    // Use jsdom for DOM testing
    environment: 'jsdom',
    // Setup files run before each test file
    setupFiles: ['./src/test/setup.ts'],
    // Include test files matching these patterns
    include: ['src/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
    // Exclude patterns
    exclude: ['node_modules', 'dist', '.idea', '.git', '.cache'],
    // Coverage configuration
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.d.ts',
        '**/*.test.{ts,tsx}',
        '**/*.spec.{ts,tsx}',
      ],
    },
    // CSS handling
    css: true,
  },
})
