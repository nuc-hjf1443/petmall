import { defineConfig } from 'vite'
import uniPlugin from '@dcloudio/vite-plugin-uni'

const uni =
  typeof uniPlugin === 'function'
    ? uniPlugin
    : typeof uniPlugin.default === 'function'
      ? uniPlugin.default
      : typeof uniPlugin.default?.default === 'function'
        ? uniPlugin.default.default
        : uniPlugin.uni

export default defineConfig({
  plugins: [uni()]
})
