import {bundle} from '@remotion/bundler';
import {renderStill, selectComposition} from '@remotion/renderer';
import {mkdtempSync, readFileSync, realpathSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

// Renders the caption preset gallery to a new JPEG. Output must be a new file under reports/ or the temp folder.
const root = path.resolve(fileURLToPath(new URL('../..', import.meta.url)));
const output = path.resolve(process.argv[2] ?? '');
const allowed = [path.join(root, 'reports'), realpathSync(tmpdir())];
if (!output.endsWith('.jpg') || !allowed.some((dir) => output.startsWith(dir + path.sep))) {
  throw new Error('Usage: gallery.mjs <reports/... or temp>.jpg');
}
const receipt = JSON.parse(readFileSync(path.join(root, '.tools/browser.json'), 'utf8'));
const browserExecutable = realpathSync(path.join(root, receipt.path));
process.chdir(path.join(root, 'renderer'));
const serveUrl = await bundle({entryPoint: path.join(root, 'renderer/src/index.tsx'),
  outDir: mkdtempSync(path.join(realpathSync(tmpdir()), 'vlog-gallery-')), enableCaching: false,
  interactivityEnabled: false, askAIEnabled: false});
const common = {serveUrl, browserExecutable, chromeMode: 'chrome-for-testing', logLevel: 'warn',
  onBrowserDownload: () => {throw new Error('Automatic browser downloads are disabled');}};
const composition = await selectComposition({...common, id: 'CaptionGallery', inputProps: {}});
await renderStill({...common, composition, inputProps: {}, frame: 30, imageFormat: 'jpeg', jpegQuality: 90,
  output, overwrite: false});
console.log(JSON.stringify({gallery: output}));
