import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Chuyển tiếp mọi request /signin ở port 5173 sang Flask port 5000
      '/signin': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/signup': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      // Để CSS/JS tĩnh của Flask (static/...) vẫn load được qua 5173
      '/static': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      // Để script signin.js/signup.js gọi /api/... vẫn chạm được backend
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
})
