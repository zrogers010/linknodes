import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

const REGISTRY_DATA_FILES = ['registry.json', 'registry_testnet.json'] as const

function serveRegistryData(): Plugin {
  const dataDir = path.resolve(__dirname, 'data')

  const copyTo = (outDir: string) => {
    const destDir = path.join(outDir, 'data')
    fs.mkdirSync(destDir, { recursive: true })
    for (const file of REGISTRY_DATA_FILES) {
      fs.copyFileSync(path.join(dataDir, file), path.join(destDir, file))
    }
  }

  return {
    name: 'serve-registry-data',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const url = req.url?.split('?')[0] ?? ''
        const match = REGISTRY_DATA_FILES.find((file) => url === `/data/${file}`)
        if (!match) {
          next()
          return
        }
        res.setHeader('Content-Type', 'application/json')
        res.setHeader('Cache-Control', 'public, max-age=300')
        fs.createReadStream(path.join(dataDir, match)).pipe(res)
      })
    },
    writeBundle(options) {
      copyTo(options.dir ?? path.resolve(__dirname, 'dist'))
    },
  }
}

export default defineConfig({
  plugins: [react(), tailwindcss(), serveRegistryData()],
  server: {
    proxy: {
      '/v1': 'http://127.0.0.1:8100',
    },
  },
})
