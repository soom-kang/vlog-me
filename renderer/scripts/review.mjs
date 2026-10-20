import {bundle} from '@remotion/bundler';
import {renderMedia, renderStill, selectComposition} from '@remotion/renderer';
import {existsSync, readFileSync, realpathSync, renameSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

// Called only by scripts/review.py while it holds the run lock. Writes inside review/vN/ only.
const root = path.resolve(fileURLToPath(new URL('../..', import.meta.url)));
const [runId, version, runDir] = process.argv.slice(2);
if (!/^prod-[a-z0-9][a-z0-9-]{0,70}$/.test(runId ?? '') || !/^[1-9][0-9]{0,3}$/.test(version ?? '')) {
  throw new Error('Usage: review.mjs prod-RUN-ID VERSION RUN-DIR');
}
// The caller passes its resolved run folder; it must be <root>/work/<runId> and locked by the caller.
const run = path.resolve(runDir ?? '');
if (path.basename(run) !== runId || path.basename(path.dirname(run)) !== 'work') throw new Error('Unexpected run folder');
if (Number(readFileSync(path.join(run, '.lock'), 'utf8')) !== process.ppid) {
  throw new Error('Review rendering must be called by the owning review.py process');
}
const folder = path.join(run, 'review', `v${version}`);
const {jobs} = JSON.parse(readFileSync(path.join(folder, 'render-input.json'), 'utf8'));
const receipt = JSON.parse(readFileSync(path.join(root, '.tools/browser.json'), 'utf8'));
const browserExecutable = realpathSync(path.join(root, receipt.path));
if (!browserExecutable.startsWith(root + path.sep)) throw new Error('Browser outside project');
const bundleDir = path.join(folder, 'bundle');
if (existsSync(bundleDir)) throw new Error('Existing review bundle; build a new review version instead');

process.chdir(path.join(root, 'renderer'));
// Proxies can be large, so the bundle links the run folder instead of copying it.
const serveUrl = await bundle({entryPoint: path.join(root, 'renderer/src/index.tsx'), publicDir: run, outDir: bundleDir,
  enableCaching: false, symlinkPublicDir: true, interactivityEnabled: false, askAIEnabled: false});
const common = {serveUrl, browserExecutable, chromeMode: 'chrome-for-testing', logLevel: 'warn',
  onBrowserDownload: () => {throw new Error('Automatic browser downloads are disabled');}};

// Media decoding occasionally stalls a frame (delayRender timeout). Keep the failed file and try once more,
// the same way render-prod.mjs does for long-form chunks.
const FRAME_TIMEOUT_MS = 120000;
const withRetry = async (label, output, render) => {
  for (let attempt = 1; ; attempt++) {
    try {
      return await render();
    } catch (error) {
      if (existsSync(output)) renameSync(output, output.replace(/(\.[a-z0-9]+)$/, `.failed-${Date.now()}$1`));
      console.log(JSON.stringify({failed: label, attempt, error: String(error).slice(0, 300)}));
      if (attempt >= 2) throw error;
    }
  }
};

for (const job of jobs) {
  const inputProps = job.props;
  const composition = await selectComposition({...common, id: 'CandidatePreview', inputProps});
  const out = path.join(folder, job.id);
  if (job.still !== false) {
    const still = path.join(out, 'expected.jpg');
    await withRetry(`${job.id}:still`, still, () => renderStill({...common, composition, inputProps, frame: job.props.keyFrame,
      imageFormat: 'jpeg', jpegQuality: 88, output: still, overwrite: false, timeoutInMilliseconds: FRAME_TIMEOUT_MS}));
  }
  if (job.preview) {
    const clip = path.join(out, 'preview.mp4');
    await withRetry(`${job.id}:preview`, clip, () => renderMedia({...common, composition, inputProps, codec: 'h264', audioCodec: 'aac',
      pixelFormat: 'yuv420p', scale: 0.5, concurrency: 4, overwrite: false, outputLocation: clip,
      timeoutInMilliseconds: FRAME_TIMEOUT_MS}));
  }
  console.log(JSON.stringify({rendered: job.id, preview: job.preview}));
}
