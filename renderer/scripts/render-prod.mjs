import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition} from '@remotion/renderer';
import {createHash} from 'node:crypto';
import {existsSync, readFileSync, realpathSync, renameSync, writeFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

// Called only by scripts/render_prod.py while it holds the run lock. Writes inside render/vN/ only.
// Video is rendered in silent chunks (resumable); the full mix is rendered once as WAV so chunk
// boundaries never cut the audio.
const root = path.resolve(fileURLToPath(new URL('../..', import.meta.url)));
const [runId, version, runDir] = process.argv.slice(2);
if (!/^prod-[a-z0-9][a-z0-9-]{0,70}$/.test(runId ?? '') || !/^[1-9][0-9]{0,3}$/.test(version ?? '')) {
  throw new Error('Usage: render-prod.mjs prod-RUN-ID VERSION RUN-DIR');
}
const run = path.resolve(runDir ?? '');
if (path.basename(run) !== runId || path.basename(path.dirname(run)) !== 'work') throw new Error('Unexpected run folder');
if (Number(readFileSync(path.join(run, '.lock'), 'utf8')) !== process.ppid) {
  throw new Error('Rendering must be called by the owning render_prod.py process');
}
const folder = path.join(run, 'render', `v${version}`);
const plan = JSON.parse(readFileSync(path.join(folder, 'render-plan.json'), 'utf8'));
const receipt = JSON.parse(readFileSync(path.join(root, '.tools/browser.json'), 'utf8'));
const browserExecutable = realpathSync(path.join(root, receipt.path));
if (!browserExecutable.startsWith(root + path.sep)) throw new Error('Browser outside project');

const sha256 = (file) => createHash('sha256').update(readFileSync(file)).digest('hex');
const manifestPath = path.join(folder, 'chunks.json');
const manifest = existsSync(manifestPath) ? JSON.parse(readFileSync(manifestPath, 'utf8')) : {props_sha256: plan.props_sha256, chunks: {}};
if (manifest.props_sha256 !== plan.props_sha256) throw new Error('Render inputs changed; start a new render version');

process.chdir(path.join(root, 'renderer'));
const bundleDir = path.join(folder, `bundle-${Date.now()}`);
const serveUrl = await bundle({entryPoint: path.join(root, 'renderer/src/index.tsx'), publicDir: run, outDir: bundleDir,
  enableCaching: false, symlinkPublicDir: true, interactivityEnabled: false, askAIEnabled: false});
const inputProps = JSON.parse(readFileSync(path.join(folder, 'props.json'), 'utf8'));
const common = {serveUrl, browserExecutable, chromeMode: 'chrome-for-testing', logLevel: 'warn', inputProps,
  onBrowserDownload: () => {throw new Error('Automatic browser downloads are disabled');}};
const composition = await selectComposition({...common, id: 'ProductionTimeline'});
const ATTEMPTS = 2;
const FRAME_TIMEOUT_MS = 120000;

// Media decoding occasionally stalls a frame (delayRender timeout). Keep the failed file for
// inspection and try once more; a later run of render_prod.py also resumes finished chunks.
const renderWithRetry = async (label, partial, options) => {
  for (let attempt = 1; ; attempt++) {
    try {
      await renderMedia({...common, composition, ...options, timeoutInMilliseconds: FRAME_TIMEOUT_MS, overwrite: false,
        outputLocation: partial});
      return;
    } catch (error) {
      if (existsSync(partial)) renameSync(partial, partial.replace(/\.partial\./, `.failed-${Date.now()}.`));
      console.log(JSON.stringify({failed: label, attempt, error: String(error).slice(0, 300)}));
      if (attempt >= ATTEMPTS) throw error;
    }
  }
};

for (const chunk of plan.chunks) {
  const final = path.join(folder, 'chunks', `${chunk.id}.mp4`);
  const done = manifest.chunks[chunk.id];
  if (done && existsSync(final) && sha256(final) === done.sha256) {
    console.log(JSON.stringify({reused: chunk.id}));
    continue;
  }
  const partial = path.join(folder, 'chunks', `${chunk.id}.partial.mp4`);
  if (existsSync(partial) || existsSync(final)) throw new Error(`Unverified chunk file ${chunk.id}; inspect it before rendering again`);
  await renderWithRetry(chunk.id, partial, {codec: 'h264', muted: true, pixelFormat: 'yuv420p', colorSpace: 'bt709',
    frameRange: [chunk.start, chunk.end - 1], concurrency: plan.concurrency});
  renameSync(partial, final);
  manifest.chunks[chunk.id] = {start: chunk.start, end: chunk.end, sha256: sha256(final)};
  writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
  console.log(JSON.stringify({rendered: chunk.id}));
}

const audio = path.join(folder, 'mix.wav');
if (!existsSync(audio)) {
  const partial = path.join(folder, 'mix.partial.wav');
  if (existsSync(partial)) throw new Error('Unverified partial mix; inspect it before rendering again');
  await renderWithRetry('mix', partial, {codec: 'wav', concurrency: plan.concurrency});
  renameSync(partial, audio);
}
console.log(JSON.stringify({status: 'chunks_and_mix_ready', chunks: plan.chunks.length}));
