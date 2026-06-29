import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const cssPath = fileURLToPath(new URL('../src/styles/main.css', import.meta.url))
const css = readFileSync(cssPath, 'utf8')

const requiredSnippets = [
  '.app-shell {\n  height: 100vh;',
  '.sidebar {\n  height: 100vh;',
  'overflow-y: auto;',
  '.main-region {\n  height: 100vh;',
  '.content {\n  flex: 1;',
  'overflow-y: auto;'
]

const missing = requiredSnippets.filter((snippet) => !css.includes(snippet))

if (missing.length) {
  console.error('Missing layout CSS snippets:')
  for (const snippet of missing) {
    console.error(`- ${snippet.replace(/\n/g, '\\n')}`)
  }
  process.exit(1)
}

console.log('Layout CSS checks passed')
