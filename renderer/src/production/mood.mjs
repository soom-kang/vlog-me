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

/** @typedef {{filter: string, tint: {color: string, blend: 'soft-light' | 'lighten'} | null}} GradeResult */
/** @param {number} value */
const rounded = (value) => Number(value.toFixed(3));

/** @param {string} grade @param {number} strength @returns {GradeResult} */
export function gradeFilter(grade, strength) {
  const s = strength;
  if (grade === 'warm') return {
    filter: `sepia(${rounded(0.18 * s)}) saturate(${rounded(1 + 0.08 * s)}) hue-rotate(${rounded(-4 * s)}deg) brightness(${rounded(1 + 0.02 * s)})`,
    tint: {color: `rgba(255,180,110,${rounded(0.07 * s)})`, blend: 'soft-light'},
  };
  if (grade === 'faded') return {
    filter: `contrast(${rounded(1 - 0.12 * s)}) saturate(${rounded(1 - 0.18 * s)}) brightness(${rounded(1 + 0.03 * s)})`,
    tint: {color: `rgba(60,50,40,${rounded(0.10 * s)})`, blend: 'lighten'},
  };
  if (grade === 'film') return {
    filter: `sepia(${rounded(0.12 * s)}) contrast(${rounded(1 - 0.08 * s)}) saturate(${rounded(1 - 0.1 * s)})`,
    tint: {color: `rgba(255,190,130,${rounded(0.06 * s)})`, blend: 'soft-light'},
  };
  return {filter: 'none', tint: null};
}

/** @param {number} aspect @param {number} width @param {number} height */
export function letterboxBar(aspect, width = 1920, height = 1080) {
  return Math.max(0, Math.round((height - width / aspect) / 2));
}
