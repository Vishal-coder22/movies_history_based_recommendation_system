import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('error', (err, req, res) => {
            if (res && !res.headersSent && typeof res.writeHead === 'function') {
              res.writeHead(502, { 'Content-Type': 'application/json' })
              res.end(
                JSON.stringify({
                  detail:
                    'Backend server is not running. Open PowerShell in the project folder and run .\\start.ps1',
                }),
              )
            }
            // Keep the real error visible in the Vite terminal for debugging.
            console.error(`[proxy] ${req.method} ${req.url} -> ${err.message}`)
          })
        },
      },
    },
  },
})
