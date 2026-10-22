import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import {softFade, narrationLineStarts, narrationSeconds} from '../src/production/mood.mjs';

const registry = JSON.parse(readFileSync(new URL('../src/production/presets.json', import.meta.url), 'utf8'));
const rules = registry.narration;

test('soft fade stays bounded on short and long cues', () => {
  for (const duration of [3, 10, 200]) {
    for (let frame = -2; frame <= duration + 2; frame++) {
      assert.ok(softFade(frame, duration, 18) >= 0 && softFade(frame, duration, 18) <= 1);
    }
    assert.equal(softFade(Math.floor(duration / 2), duration, 18), 1);
    assert.equal(softFade(0, duration, 18), 0);
    assert.equal(softFade(duration, duration, 18), 0);
  }
});

test('narration starts preserve reading order and reserve the last second', () => {
  assert.deepEqual(narrationLineStarts(['하나'], 120, 30, rules), [0]);
  const starts = narrationLineStarts(['오늘은 천천히', '바람이 먼저 왔다', '충분했다'], 120, 30, rules);
  assert.ok(starts[1] > starts[0] && starts[2] > starts[1]);
  assert.ok(starts[2] <= 120 - rules.fade_frames - 30);
  assert.deepEqual(narrationLineStarts(['하나', '둘', '셋'], 10, 30, rules), [0, 0, 0]);
  assert.deepEqual(narrationLineStarts([], 10, 30, rules), []);
});

test('narration reading time matches the Python contract', () => {
  assert.ok(Math.abs(narrationSeconds('가나다라마바사아자차', rules) - 3.3) < 1e-10);
  assert.ok(Math.abs(narrationSeconds('가 나\n다 라', rules) - 3.18) < 1e-10);
  assert.equal(narrationSeconds('가', rules), 2.5);
});
