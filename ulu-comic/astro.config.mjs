import { defineConfig } from 'astro/config';

// Static build. CSS is inlined so dist/index.html works from any host or sub-path.
export default defineConfig({
  site: 'https://korirjr.github.io',
  base: '/Fed',
  build: { inlineStylesheets: 'always' },
  compressHTML: true,
  scopedStyleStrategy: 'where',
});
