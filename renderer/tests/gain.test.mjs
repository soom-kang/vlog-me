import test from 'node:test';
import assert from 'node:assert/strict';
import {gainAt} from '../src/gain.mjs';

test('dB ducking converts to amplitude without boosting source', () => {
  const points = [[0, -6], [30, -18], [60, -18], [90, -6]];
  assert.ok(Math.abs(gainAt(45, points) - 0.1258925) < 0.000001);
  assert.ok(gainAt(45, points) < gainAt(0, points) / 3);
  assert.equal(gainAt(0, points), gainAt(90, points));
});
test('fade interpolates in dB and clamps outside cue', () => {
  const points = [[0, -60], [30, 0]];
  assert.equal(gainAt(-10, points), 0.001);
  assert.ok(Math.abs(gainAt(15, points) - 10 ** (-30 / 20)) < 1e-10);
  assert.equal(gainAt(40, points), 1);
});
