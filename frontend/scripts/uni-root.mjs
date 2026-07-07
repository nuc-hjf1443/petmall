import { spawn } from 'node:child_process'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDir = dirname(fileURLToPath(import.meta.url))
const projectRoot = resolve(scriptDir, '..')

process.env.UNI_INPUT_DIR ||= projectRoot
process.env.UNI_OUTPUT_DIR ||= join(projectRoot, 'unpackage', 'dist', 'build', 'h5')

const uniBin = join(projectRoot, 'node_modules', '@dcloudio', 'vite-plugin-uni', 'bin', 'uni.js')
const child = spawn(process.execPath, [uniBin, ...process.argv.slice(2)], {
  cwd: projectRoot,
  env: process.env,
  stdio: 'inherit',
})

child.on('error', error => {
  console.error(error)
  process.exit(1)
})

child.on('exit', code => {
  process.exit(code ?? 1)
})
