import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import fs from 'fs'
import path from 'path'

const esToolkitCompatPlugin = () => {
  return {
    name: 'es-toolkit-compat',
    resolveId(id: string) {
      if (id.startsWith('es-toolkit/compat/')) {
        return id;
      }
      return null;
    },
    load(id: string) {
      if (id.startsWith('es-toolkit/compat/')) {
        const name = id.replace('es-toolkit/compat/', '');
        const subdirs = ['array', 'function', 'math', 'object', 'predicate', 'string', 'util'];
        
        try {
          const basePath = path.dirname(require.resolve('es-toolkit/package.json', { paths: [process.cwd()] }));
          
          for (const subdir of subdirs) {
            const filePath = path.join(basePath, 'dist', 'compat', subdir, `${name}.mjs`);
            if (fs.existsSync(filePath)) {
              return `import { ${name} } from 'es-toolkit/dist/compat/${subdir}/${name}.mjs';\nexport default ${name};`;
            }
          }
          
          // Check root dist/compat
          const rootFilePath = path.join(basePath, 'dist', 'compat', `${name}.mjs`);
          if (fs.existsSync(rootFilePath)) {
            return `import { ${name} } from 'es-toolkit/dist/compat/${name}.mjs';\nexport default ${name};`;
          }
        } catch (err) {
          console.error('es-toolkit-compat plugin error resolving:', id, err);
        }
      }
      return null;
    }
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss(), esToolkitCompatPlugin()],
})


