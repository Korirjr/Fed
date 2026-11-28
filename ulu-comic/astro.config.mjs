import { defineConfig } from 'astro/config';

// Static build. CSS is inlined so dist/index.html works from any host or sub-path.
export default defineConfig({
  site: 'https://ulu.app',
  build: { inlineStylesheets: 'always' },
  compressHTML: true,
  scopedStyleStrategy: 'where',
});
