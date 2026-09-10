// libvips/librsvg preserves SVG masks and filters used by Gerbonara's preview.
const path = require('node:path');
const sharp = require('/Users/chris/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
(async () => {
  const root = path.resolve(process.argv[2]);
  for (const side of ['top', 'bottom']) {
    await sharp(path.join(root, `gerber-${side}.svg`), { density: 600 })
      .resize({ width: 1500 }).png().toFile(path.join(root, `gerber-${side}.png`));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
