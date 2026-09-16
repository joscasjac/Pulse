import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import frappeui from 'frappe-ui/vite'
import path from 'path'

export default defineConfig({
  plugins: [
    {
      name: 'pulse-stable-mention-popup',
      enforce: 'pre',
      resolveId(source, importer) {
        // TipTap 3 starts suggestions before async items arrive. Keep a stable
        // element for Frappe UI's popup renderer even when that list is empty.
        if (source === '../suggestion/SuggestionList.vue' && importer?.endsWith('/mention/mention-extension.ts')) {
          return path.resolve(__dirname, 'src/components/documents/MentionSuggestions.vue')
        }
      },
    },
    frappeui({
      frontendRoute: '/pulse',
      lucideIcons: true,
      frappeProxy: true,
      jinjaBootData: true,
      buildConfig: {
        outDir: '../pulse/public/frontend',
        emptyOutDir: true,
        indexHtmlPath: '../pulse/www/pulse.html',
      },
    }),
    vue(),
  ],
  resolve: {
    alias: { '@': path.resolve(__dirname, 'src') },
  },
  server: {
    host: '0.0.0.0',
    port: 8080,
  },
})
