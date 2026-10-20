import type {CSSProperties, ReactNode} from 'react';
import {Easing, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {FONTS, ensureFonts} from './fonts';

export type CaptionCue = {
  id: string; kind: string; preset: string; text: string; position: string;
  speaker?: string | null; sub?: string | null; from: number; duration: number;
};

// Variety (예능) presets carry the jokes (target ~80% of styled captions); mood presets stay quiet and refined.
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
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

const speakerColor = (speaker: string | null | undefined, fallback: string) => {
  if (!speaker) return fallback;
  let hash = 0;
  for (const char of speaker) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return SPEAKER_COLORS[hash % SPEAKER_COLORS.length];
};

type Motion = {pop: number; fade: number; frame: number; duration: number};

const titleBox = (background: string, color: string, border: string) => (_cue: CaptionCue, {pop}: Motion): CSSProperties => ({
  fontFamily: FONTS.cute, fontSize: 48, color, background, padding: '10px 26px', borderRadius: 16, border,
  transform: `translateY(${(1 - pop) * -36}px)`});

// Text-only presets: a style per frame. Outlined ones are drawn as two layers (see Caption below).
const STYLES: Record<string, (cue: CaptionCue, m: Motion) => CSSProperties> = {
  pop: (cue, {pop}) => ({fontFamily: FONTS.variety, fontSize: 104, color: speakerColor(cue.speaker, '#ffffff'),
    ...outline('#111111', 16), textShadow: '0 10px 0 #ffcc00', transform: `scale(${0.55 + 0.45 * pop})`}),
  shout: (_cue, {pop, frame}) => ({fontFamily: FONTS.variety, fontSize: 128, color: '#ffe14d', ...outline('#d6281e', 16),
    transform: `scale(${0.7 + 0.3 * pop}) rotate(${frame < 12 ? Math.sin(frame * 2.4) * 4 : 0}deg)`}),
  punch: (cue, {frame}) => ({fontFamily: FONTS.variety, fontSize: 110, color: speakerColor(cue.speaker, '#ff7eb6'),
    ...outline('#ffffff', 14), textShadow: '0 8px 0 #2b2b2b',
    transform: `scale(${interpolate(frame, [0, 6], [1.7, 1], clamp)})`}),
  drop: (cue, {frame}) => ({fontFamily: FONTS.variety, fontSize: 108, color: speakerColor(cue.speaker, '#8ff0ff'),
    ...outline('#10324a', 15), textShadow: '0 9px 0 #ffffff',
    transform: `translateY(${interpolate(frame, [0, 7, 11, 14], [-260, 18, -8, 0], clamp)}px)`}),
  shake: (_cue, {pop, frame}) => ({fontFamily: FONTS.variety, fontSize: 112, color: '#ffffff', ...outline('#5a2fd0', 15),
    textShadow: '0 8px 0 #c9b6ff',
    transform: `scale(${0.7 + 0.3 * pop}) translate(${Math.sin(frame * 1.9) * 5}px, ${Math.cos(frame * 2.3) * 4}px)`}),
  'box-yellow': titleBox('#ffd84d', '#2b2100', '5px solid #2b2100'),
  'box-dark': titleBox('rgba(17,17,17,0.78)', '#ffffff', 'none'),
  'box-pink': titleBox('#ff9cc2', '#3a0d20', '5px solid #3a0d20'),
  'box-mint': titleBox('#8ff0cf', '#0d3327', '5px solid #0d3327'),
  'box-sky': titleBox('#9ad4ff', '#0b2540', '5px solid #0b2540'),
  ribbon: (_cue, {frame}) => ({fontFamily: FONTS.cute, fontSize: 48, color: '#ffffff', background: '#ff5a5f',
    padding: '10px 34px', transform: `skewX(-12deg) translateX(${interpolate(frame, [0, 8], [-420, 0], {...clamp,
      easing: Easing.out(Easing.cubic)})}px)`, boxShadow: '8px 8px 0 #2b2b2b'}),
  sticker: (_cue, {pop}) => ({fontFamily: FONTS.cute, fontSize: 50, color: '#2b2b2b', background: '#ffffff',
    padding: '12px 28px', borderRadius: 999, border: '6px solid #2b2b2b', boxShadow: '0 10px 0 #2b2b2b',
    transform: `rotate(-4deg) scale(${0.4 + 0.6 * pop})`}),
  stamp: (_cue, {frame}) => ({fontFamily: FONTS.sfx, fontSize: 56, color: '#e23b3b', padding: '6px 22px',
    border: '6px solid #e23b3b', borderRadius: 10, background: 'rgba(255,255,255,0.88)',
    transform: `rotate(-8deg) scale(${interpolate(frame, [0, 5, 8], [2.2, 0.92, 1], clamp)})`}),
  'tilt-red': (_cue, {pop}) => ({fontFamily: FONTS.sfx, fontSize: 140, color: '#ff3b3b', ...outline('#ffffff', 14),
    transform: `rotate(-10deg) scale(${0.3 + 0.7 * pop})`}),
  'tilt-blue': (_cue, {pop}) => ({fontFamily: FONTS.sfx, fontSize: 140, color: '#3b8bff', ...outline('#ffffff', 14),
    transform: `rotate(9deg) scale(${0.3 + 0.7 * pop})`}),
  burst: (_cue, {frame}) => ({fontFamily: FONTS.sfx, fontSize: 150, color: '#ffe14d', ...outline('#111111', 16),
    transform: `scale(${interpolate(frame, [0, 4, 9], [0.2, 1.35, 1], clamp)})`}),
  whoosh: (_cue, {frame}) => ({fontFamily: FONTS.sfx, fontSize: 132, color: '#ffffff', ...outline('#1d6fd6', 13),
    fontStyle: 'italic', transform: `translateX(${interpolate(frame, [0, 6], [500, 0], {...clamp,
      easing: Easing.out(Easing.cubic)})}px) skewX(${interpolate(frame, [0, 6], [-30, -10], clamp)}deg)`}),
  'pen-sfx': (_cue, {pop}) => ({fontFamily: FONTS.pen, fontSize: 150, color: '#fff7c2', ...outline('#3a2a00', 10),
    transform: `rotate(-6deg) scale(${0.5 + 0.5 * pop})`}),
  bracket: (_cue, {fade}) => ({fontFamily: FONTS.cute, fontSize: 62, color: '#bfe3ff', ...outline('#0b2540', 11), opacity: fade}),
  whisper: (_cue, {fade}) => ({fontFamily: FONTS.cute, fontSize: 48, color: '#e8e8e8', ...outline('#3a3a3a', 8), opacity: fade * 0.9}),
  'pen-note': (_cue, {fade, frame}) => ({fontFamily: FONTS.pen, fontSize: 84, color: '#fffdf2', ...outline('#2b2b2b', 7),
    opacity: fade, transform: `rotate(-3deg) translateY(${interpolate(frame, [0, 10], [14, 0], clamp)}px)`}),
  dialogue: (cue) => ({fontFamily: FONTS.dialogue, fontSize: 58, color: speakerColor(cue.speaker, '#ffffff'), ...outline('#111111', 10)}),
  'dialogue-box': (cue) => ({fontFamily: FONTS.dialogue, fontSize: 52, color: speakerColor(cue.speaker, '#ffffff'),
    background: 'rgba(0,0,0,0.55)', padding: '8px 22px', borderRadius: 10}),
  'serif-fade': (_cue, {fade}) => ({fontFamily: FONTS.serif, fontSize: 56, color: '#fffaf0', opacity: fade,
    textShadow: '0 2px 14px rgba(0,0,0,0.6)', letterSpacing: 3}),
  'serif-low': (_cue, {fade}) => ({fontFamily: FONTS.serif, fontSize: 44, color: '#fffaf0', opacity: fade,
    textShadow: '0 2px 12px rgba(0,0,0,0.6)', letterSpacing: 2, transform: `translateY(${(1 - fade) * 16}px)`}),
  'pen-script': (_cue, {fade}) => ({fontFamily: FONTS.pen, fontSize: 88, color: '#fffaf0', opacity: fade,
    textShadow: '0 2px 16px rgba(0,0,0,0.55)'}),
  'place-card': (_cue, {fade}) => ({fontFamily: FONTS.serif, fontSize: 42, color: '#fffaf0', opacity: fade,
    borderLeft: '5px solid #fffaf0', paddingLeft: 20, textShadow: '0 2px 10px rgba(0,0,0,0.55)', letterSpacing: 2}),
};

const soft = '0 2px 18px rgba(0,0,0,0.55)';

// Presets with their own layout: speech bubbles and the editorial mood titles.
const LAYOUTS: Record<string, (cue: CaptionCue, m: Motion) => ReactNode> = {
  bubble: (cue, {pop}) => (
    <div style={{position: 'relative', transform: `scale(${0.3 + 0.7 * pop})`, transformOrigin: '20% 100%'}}>
      <div style={{fontFamily: FONTS.cute, fontSize: 50, color: '#1d1d1b', background: '#ffffff', padding: '16px 30px',
        borderRadius: 36, border: '5px solid #1d1d1b', whiteSpace: 'pre-wrap', textAlign: 'center'}}>{cue.text}</div>
      <div style={{position: 'absolute', left: 60, bottom: -26, width: 0, height: 0, borderLeft: '18px solid transparent',
        borderRight: '18px solid transparent', borderTop: '30px solid #1d1d1b'}} />
      <div style={{position: 'absolute', left: 65, bottom: -16, width: 0, height: 0, borderLeft: '13px solid transparent',
        borderRight: '13px solid transparent', borderTop: '22px solid #ffffff'}} />
    </div>
  ),
  thought: (cue, {fade}) => (
    <div style={{position: 'relative', opacity: fade}}>
      <div style={{fontFamily: FONTS.cute, fontSize: 48, color: '#2b2b4a', background: '#f3f0ff', padding: '18px 34px',
        borderRadius: 60, boxShadow: '0 6px 0 rgba(43,43,74,0.35)', whiteSpace: 'pre-wrap', textAlign: 'center'}}>{cue.text}</div>
      {[[34, -26, 26], [12, -50, 16]].map(([left, bottom, size]) => (
        <div key={left} style={{position: 'absolute', left, bottom, width: size, height: size, borderRadius: '50%',
          background: '#f3f0ff', boxShadow: '0 4px 0 rgba(43,43,74,0.35)'}} />
      ))}
    </div>
  ),
  editorial: (cue, {frame, duration}) => {
    const reveal = interpolate(frame, [0, 18], [0, 1], {...clamp, easing: Easing.out(Easing.cubic)});
    const out = interpolate(frame, [duration - 12, duration], [1, 0], clamp);
    return (
      <div style={{textAlign: 'center', color: '#fffaf0', opacity: reveal * out, textShadow: soft}}>
        <div style={{fontFamily: FONTS.serif, fontSize: 72, letterSpacing: 10 - 4 * reveal, whiteSpace: 'pre-wrap',
          filter: `blur(${(1 - reveal) * 6}px)`}}>{cue.text}</div>
        {cue.sub ? (
          <div style={{fontFamily: FONTS.latin, fontStyle: 'italic', fontSize: 40, letterSpacing: 4, marginTop: 14,
            opacity: interpolate(frame, [10, 26], [0, 0.9], clamp)}}>{cue.sub}</div>
        ) : null}
      </div>
    );
  },
  'letter-fade': (cue, {frame, duration}) => {
    const out = interpolate(frame, [duration - 12, duration], [1, 0], clamp);
    return (
      <div style={{fontFamily: FONTS.serif, fontSize: 60, letterSpacing: 6, color: '#fffaf0', textShadow: soft,
        opacity: out, whiteSpace: 'pre-wrap', textAlign: 'center'}}>
        {Array.from(cue.text).map((char, index) => {
          const t = interpolate(frame, [index * 2.5, index * 2.5 + 12], [0, 1], clamp);
          return <span key={index} style={{opacity: t, filter: `blur(${(1 - t) * 8}px)`,
            display: 'inline-block', transform: `translateY(${(1 - t) * 10}px)`}}>{char === ' ' ? ' ' : char}</span>;
        })}
      </div>
    );
  },
  'film-line': (cue, {fade}) => (
    <div style={{textAlign: 'center', color: '#fffaf0', opacity: fade, textShadow: soft}}>
      <div style={{width: 120 + 240 * fade, height: 2, background: '#fffaf0', margin: '0 auto 18px', opacity: 0.8}} />
      <div style={{fontFamily: FONTS.serif, fontSize: 50, letterSpacing: 6, whiteSpace: 'pre-wrap'}}>{cue.text}</div>
      {cue.sub ? <div style={{fontFamily: FONTS.latin, fontSize: 30, letterSpacing: 8, marginTop: 10,
        textTransform: 'uppercase'}}>{cue.sub}</div> : null}
      <div style={{width: 120 + 240 * fade, height: 2, background: '#fffaf0', margin: '18px auto 0', opacity: 0.8}} />
    </div>
  ),
  'place-editorial': (cue, {fade, frame}) => (
    <div style={{color: '#fffaf0', opacity: fade, textShadow: soft}}>
      <div style={{fontFamily: FONTS.latin, fontSize: 64, fontWeight: 500, letterSpacing: 14 - 6 * fade,
        textTransform: 'uppercase'}}>{cue.sub ?? cue.text}</div>
      <div style={{display: 'flex', alignItems: 'center', gap: 16, marginTop: 6}}>
        <div style={{width: interpolate(frame, [4, 20], [0, 90], clamp), height: 2, background: '#fffaf0'}} />
        <div style={{fontFamily: FONTS.serif, fontSize: 34, letterSpacing: 4}}>{cue.text}</div>
      </div>
    </div>
  ),
};

export const PRESET_NAMES = [...Object.keys(STYLES), ...Object.keys(LAYOUTS)];

export const Caption = ({cue}: {cue: CaptionCue}) => {
  // Load fonts on first caption only, so compositions without captions (synthetic setup) never wait on them.
  ensureFonts();
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({frame, fps, config: {damping: 11, stiffness: 180}});
  const fade = interpolate(frame, [0, 8, cue.duration - 8, cue.duration], [0, 1, 1, 0], clamp);
  const motion = {pop, fade, frame, duration: cue.duration};
  const wrap: CSSProperties = {position: 'absolute', display: 'flex', ...(POSITIONS[cue.position] ?? POSITIONS.bottom)};
  if (LAYOUTS[cue.preset]) {
    return <div style={wrap}>{LAYOUTS[cue.preset](cue, motion)}</div>;
  }
  const style = (STYLES[cue.preset] ?? STYLES.dialogue)(cue, motion);
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
