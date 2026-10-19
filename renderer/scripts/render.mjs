import {bundle} from '@remotion/bundler';
import {selectComposition, renderMedia} from '@remotion/renderer';
import {readFileSync, existsSync, realpathSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

const root = path.resolve(fileURLToPath(new URL('../..', import.meta.url)));
const runId = process.argv[2];
if (!/^synthetic-[a-z0-9][a-z0-9-]{0,70}$/.test(runId ?? '')) throw new Error('Only synthetic run IDs supported');
// Reuse the canonical validator before any bundle or media write.
execFileSync('python3', [path.join(root, 'scripts/validate.py'), '--run-id', runId, '--for-render'], {cwd: root, stdio: 'pipe'});
const run = path.join(root, 'work', runId);
if (Number(readFileSync(path.join(run, '.lock'), 'utf8')) !== process.ppid) {
  throw new Error('Render must be called by the owning synthetic.py process');
}
const manifest = JSON.parse(readFileSync(path.join(run, 'fixture-manifest.json')));
const timeline = JSON.parse(readFileSync(path.join(run, 'timeline.json')));
const profile = JSON.parse(readFileSync(path.join(run, 'brief.json'))).resolved_config.synthetic_profile;
const inputProps = {timeline, assets: manifest.assets};
const receipt = JSON.parse(readFileSync(path.join(root, '.tools/browser.json')));
const browserExecutable = realpathSync(path.join(root, receipt.path));
if (!browserExecutable.startsWith(root + path.sep)) throw new Error('Browser outside project');
const output = path.join(run, 'preview.partial.mp4');
const bundleDir = path.join(run, 'bundle');
if (existsSync(output) || existsSync(bundleDir) || existsSync(path.join(run, 'preview.mp4'))) {
  throw new Error('Existing render output; create a fresh synthetic run instead of overwriting');
}
process.chdir(path.join(root, 'renderer'));
const serveUrl = await bundle({entryPoint: path.join(root, 'renderer/src/index.tsx'),
  publicDir: path.join(run, 'assets'), outDir: bundleDir, enableCaching: false,
  symlinkPublicDir: false, interactivityEnabled: false, askAIEnabled: false});
const composition = await selectComposition({serveUrl, id: 'VlogSetup', inputProps, browserExecutable, chromeMode: 'chrome-for-testing'});
await renderMedia({serveUrl, composition, inputProps, browserExecutable, outputLocation: output,
  codec: 'h264', audioCodec: 'aac', pixelFormat: 'yuv420p', colorSpace: 'bt709',
  concurrency: profile.concurrency, overwrite: false, timeoutInMilliseconds: 60000, logLevel: 'warn', chromeMode: 'chrome-for-testing',
  onBrowserDownload: () => {throw new Error('Automatic browser downloads are disabled during checks');}});
console.log(JSON.stringify({status: 'rendered_partial_pending_verification', duration_frames: timeline.duration_frames}));
