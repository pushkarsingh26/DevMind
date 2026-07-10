import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],

  build: {
    target: 'esnext',
    minify: 'oxc',
    cssMinify: true,
    reportCompressedSize: false, // speeds up build
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          // Core React runtime — always first to load
          if (id.includes('node_modules/react') || id.includes('node_modules/react-dom')) {
            return 'react';
          }
          // Framer Motion — large, loaded after core
          if (id.includes('node_modules/framer-motion')) {
            return 'framer-motion';
          }
          // Markdown + syntax highlighting — lazy-loaded pages only
          if (id.includes('node_modules/react-markdown') || id.includes('node_modules/rehype') || id.includes('node_modules/remark') || id.includes('node_modules/highlight.js') || id.includes('node_modules/unified') || id.includes('node_modules/hast') || id.includes('node_modules/mdast')) {
            return 'markdown';
          }
          // Lucide icon tree — separate chunk
          if (id.includes('node_modules/lucide-react')) {
            return 'icons';
          }
          // Network layer
          if (id.includes('node_modules/axios')) {
            return 'axios';
          }
          // React Router
          if (id.includes('node_modules/react-router')) {
            return 'router';
          }
        },
      },
    },
  },

  optimizeDeps: {
    include: ['react', 'react-dom', 'react-router-dom', 'framer-motion'],
  },
})
