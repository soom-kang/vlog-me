import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import {softFade, narrationLineStarts, narrationSeconds, gradeFilter, letterboxBar, lightLeakOpacity} from '../src/production/mood.mjs';

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

test('grade filters and tint use bounded deterministic coefficients', () => {
  assert.deepEqual(gradeFilter('none', 0.6), {filter: 'none', tint: null});
  assert.ok(gradeFilter('warm', 0).filter.includes('sepia(0)'));
  for (const grade of registry.look.grades) assert.equal(typeof gradeFilter(grade, 0.5).filter, 'string');
  assert.deepEqual(gradeFilter('warm', 0.5), {
    filter: 'sepia(0.09) saturate(1.04) hue-rotate(-2deg) brightness(1.01)',
    tint: {color: 'rgba(255,180,110,0.035)', blend: 'soft-light'},
  });
  assert.equal(gradeFilter('faded', 0.5).tint.blend, 'lighten');
});

test('letterbox dimensions match the 1080p contract', () => {
  assert.equal(letterboxBar(2.39), 138);
  assert.equal(letterboxBar(2.0), 60);
  assert.equal(letterboxBar(1), 0);
});

test('light leak has a capped plateau and clamps short cues', () => {
  for (const duration of [1, 3, 15, 60]) {
    for (let frame = -1; frame <= duration + 1; frame++) {
      const value = lightLeakOpacity(frame, duration, 2);
      assert.ok(value >= 0 && value <= 0.5);
    }
    assert.equal(lightLeakOpacity(0, duration, 1), 0);
    assert.equal(lightLeakOpacity(duration, duration, 1), 0);
  }
  assert.equal(lightLeakOpacity(30, 60, 2), 0.5);
  assert.equal(lightLeakOpacity(30, 60, 1), 0.3);
});

test('gallery still shows all narration lines and subtitle before fade-out', () => {
  const lines = ['오늘은 조금 천천히 걷기로 했다', '바람이 먼저 와 있었다', '그걸로 충분했다'];
  const starts = narrationLineStarts(lines, 180, 30, rules);
  assert.deepEqual(starts, [0, 65, 115]);
  const localFrame = 30 + 120;
  assert.ok(starts.at(-1) + rules.fade_frames * 2 <= localFrame);
  assert.ok(localFrame < 180 - rules.fade_frames);
  assert.equal(softFade(localFrame, 180, registry.soft_fade_frames), 1);
  assert.ok(localFrame < 180 - 12); // Existing layout fade-outs start no earlier than frame 168.
});
