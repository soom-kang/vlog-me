import type {CSSProperties} from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {FONTS, ensureFonts} from './fonts';

export type CaptionCue = {
  id: string; kind: string; preset: string; text: string; position: string;
  speaker?: string | null; from: number; duration: number;
};


// Variety (예능) presets carry the jokes (target ~80% of styled captions); mood presets stay quiet.
// Preset names must match presets.json, which the Python validators also read.
const SPEAKER_COLORS = ['#ffe14d', '#7fe0ff', '#ff9ec7', '#b6f36b'];

const POSITIONS: Record<string, CSSProperties> = {
  bottom: {left: 0, right: 0, bottom: 80, justifyContent: 'center'},
  top: {left: 0, right: 0, top: 70, justifyContent: 'center'},
  center: {left: 0, right: 0, top: 440, justifyContent: 'center'},
  upper_left: {left: 80, top: 64},
  upper_right: {right: 80, top: 140},
  lower_left: {left: 80, bottom: 120},
  lower_right: {right: 80, bottom: 120},
};

const outline = (color: string, width: number): CSSProperties => ({WebkitTextStroke: `${width}px ${color}`});

const speakerColor = (speaker: string | null | undefined, fallback: string) => {
  if (!speaker) return fallback;
  let hash = 0;
  for (const char of speaker) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return SPEAKER_COLORS[hash % SPEAKER_COLORS.length];
};

type Motion = {pop: number; fade: number; frame: number};

const PRESETS: Record<string, (cue: CaptionCue, m: Motion) => CSSProperties> = {
  pop: (cue, {pop}) => ({fontFamily: FONTS.variety, fontSize: 104, color: speakerColor(cue.speaker, '#ffffff'),
    ...outline('#111111', 16), textShadow: '0 10px 0 #ffcc00', transform: `scale(${0.55 + 0.45 * pop})`}),
  shout: (_cue, {pop, frame}) => ({fontFamily: FONTS.variety, fontSize: 128, color: '#ffe14d', ...outline('#d6281e', 16),
    transform: `scale(${0.7 + 0.3 * pop}) rotate(${frame < 12 ? Math.sin(frame * 2.4) * 4 : 0}deg)`}),
  punch: (cue, {frame}) => ({fontFamily: FONTS.variety, fontSize: 110, color: speakerColor(cue.speaker, '#ff7eb6'),
    ...outline('#ffffff', 14), textShadow: '0 8px 0 #2b2b2b',
    transform: `scale(${interpolate(frame, [0, 6], [1.7, 1], {extrapolateRight: 'clamp'})})`}),
  'box-yellow': (_cue, {pop}) => ({fontFamily: FONTS.cute, fontSize: 48, color: '#2b2100', background: '#ffd84d',
    padding: '10px 24px', borderRadius: 16, border: '5px solid #2b2100', transform: `translateY(${(1 - pop) * -36}px)`}),
  'box-dark': (_cue, {pop}) => ({fontFamily: FONTS.cute, fontSize: 46, color: '#ffffff', background: 'rgba(17,17,17,0.78)',
    padding: '10px 24px', borderRadius: 12, transform: `translateY(${(1 - pop) * -36}px)`}),
  'tilt-red': (_cue, {pop}) => ({fontFamily: FONTS.sfx, fontSize: 140, color: '#ff3b3b', ...outline('#ffffff', 14),
    transform: `rotate(-10deg) scale(${0.3 + 0.7 * pop})`}),
  'tilt-blue': (_cue, {pop}) => ({fontFamily: FONTS.sfx, fontSize: 140, color: '#3b8bff', ...outline('#ffffff', 14),
    transform: `rotate(9deg) scale(${0.3 + 0.7 * pop})`}),
  burst: (_cue, {frame}) => ({fontFamily: FONTS.sfx, fontSize: 150, color: '#ffe14d', ...outline('#111111', 16),
    transform: `scale(${interpolate(frame, [0, 4, 9], [0.2, 1.35, 1], {extrapolateRight: 'clamp'})})`}),
  bracket: (_cue, {fade}) => ({fontFamily: FONTS.cute, fontSize: 62, color: '#bfe3ff', ...outline('#0b2540', 11), opacity: fade}),
  whisper: (_cue, {fade}) => ({fontFamily: FONTS.cute, fontSize: 48, color: '#e8e8e8', ...outline('#3a3a3a', 8), opacity: fade * 0.9}),
  dialogue: (cue) => ({fontFamily: FONTS.dialogue, fontSize: 58, color: speakerColor(cue.speaker, '#ffffff'), ...outline('#111111', 10)}),
  'serif-fade': (_cue, {fade}) => ({fontFamily: FONTS.serif, fontSize: 56, color: '#fffaf0', opacity: fade,
    textShadow: '0 2px 14px rgba(0,0,0,0.6)', letterSpacing: 3}),
  'serif-low': (_cue, {fade}) => ({fontFamily: FONTS.serif, fontSize: 44, color: '#fffaf0', opacity: fade,
    textShadow: '0 2px 12px rgba(0,0,0,0.6)', letterSpacing: 2, transform: `translateY(${(1 - fade) * 16}px)`}),
  'place-card': (_cue, {fade}) => ({fontFamily: FONTS.serif, fontSize: 42, color: '#fffaf0', opacity: fade,
    borderLeft: '5px solid #fffaf0', paddingLeft: 20, textShadow: '0 2px 10px rgba(0,0,0,0.55)', letterSpacing: 2}),
};

export const PRESET_NAMES = Object.keys(PRESETS);

export const Caption = ({cue}: {cue: CaptionCue}) => {
  // Load fonts on first caption only, so compositions without captions (synthetic setup) never wait on them.
  ensureFonts();
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({frame, fps, config: {damping: 11, stiffness: 180}});
  const fade = interpolate(frame, [0, 8, cue.duration - 8, cue.duration], [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const style = (PRESETS[cue.preset] ?? PRESETS.dialogue)(cue, {pop, fade, frame});
  const wrap: CSSProperties = {position: 'absolute', display: 'flex', ...(POSITIONS[cue.position] ?? POSITIONS.bottom)};
  const {WebkitTextStroke, textShadow, ...box} = style;
  const base: CSSProperties = {...box, whiteSpace: 'pre-wrap', textAlign: 'center', lineHeight: 1.15, maxWidth: 1600};
  if (!WebkitTextStroke) {
    return <div style={wrap}><div style={{...base, textShadow}}>{cue.text}</div></div>;
  }
  // Chrome ignores paint-order on HTML text, so the stroke sits on a back layer and the fill is drawn on top.
  return (
    <div style={wrap}>
      <div style={{...base, position: 'relative'}}>
        <span style={{WebkitTextStroke, textShadow}}>{cue.text}</span>
        <span style={{position: 'absolute', left: 0, top: 0, width: '100%'}} aria-hidden>{cue.text}</span>
      </div>
    </div>
  );
};
