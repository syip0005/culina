import { defineConfig } from 'vite'
import { TanStackRouterVite } from '@tanstack/router-plugin/vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [
    TanStackRouterVite({ routesDirectory: './src/routes', autoCodeSplitting: true }),
    react(),
  ],
  server: { port: 3000 },
})
