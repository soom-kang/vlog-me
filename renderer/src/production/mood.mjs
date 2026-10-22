/** Shared deterministic timing for mood captions; no React or browser dependencies. */
/** @typedef {{read_base_seconds: number, read_per_char_seconds: number, min_seconds: number, fade_frames: number}} NarrationRules */

/** @param {number} value */
const clamp01 = (value) => Math.max(0, Math.min(1, value));

/** @param {number} frame @param {number} duration @param {number} frames */
export function softFade(frame, duration, frames) {
  const f = Math.max(1, Math.min(frames, Math.floor((duration - 1) / 2)));
  return clamp01(Math.min(frame / f, (duration - frame) / f));
}

/** @param {string} line @param {NarrationRules} rules */
export function narrationLineSeconds(line, rules) {
  return rules.read_base_seconds + rules.read_per_char_seconds * Array.from(line.replace(/\s/g, '')).length;
}

/** @param {string[]} lines @param {number} duration @param {number} fps @param {NarrationRules} rules */
export function narrationLineStarts(lines, duration, fps, rules) {
  let cursor = 0;
  const starts = lines.map((line) => {
    const start = cursor;
    cursor += Math.round(fps * narrationLineSeconds(line, rules));
    return start;
  });
  const last = starts.at(-1) ?? 0;
  const limit = Math.max(0, duration - rules.fade_frames - fps);
  return last > limit ? starts.map((start) => Math.round(start * limit / last)) : starts;
}

/** @param {string} text @param {NarrationRules} rules */
export function narrationSeconds(text, rules) {
  const reading = text.split('\n').reduce((sum, line) => sum + narrationLineSeconds(line, rules), 0);
  return Math.max(rules.min_seconds, reading + rules.fade_frames / 30 + 1);
}
