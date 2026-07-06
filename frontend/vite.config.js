import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import frappeui from 'frappe-ui/vite'
import path from 'path'

export default defineConfig({
  plugins: [
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
