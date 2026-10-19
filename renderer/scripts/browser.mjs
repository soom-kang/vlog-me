import {ensureBrowser} from '@remotion/renderer';
import {writeFileSync, existsSync, realpathSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

const root = path.resolve(fileURLToPath(new URL('../..', import.meta.url)));
process.chdir(path.join(root, 'renderer'));
const receipt = path.join(root, '.tools/browser.json');
if (existsSync(receipt)) throw new Error('Browser receipt exists; inspect before replacing it.');
const result = await ensureBrowser({chromeMode: 'chrome-for-testing'});
if (!('path' in result)) throw new Error(`Browser unavailable: ${result.type}`);
const browser = realpathSync(result.path);
if (!browser.startsWith(root + path.sep)) throw new Error('Expected a project-local browser');
writeFileSync(receipt, JSON.stringify({path: path.relative(root, browser), remotion: '4.0.536', chromeMode: 'chrome-for-testing'}, null, 2) + '\n', {flag: 'wx'});
console.log('Project-local rendering browser ready.');
