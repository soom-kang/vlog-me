import type {CSSProperties} from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

export type CaptionCue = {
  id: string; kind: string; preset: string; text: string; position: string;
  speaker?: string | null; from: number; duration: number;
};

// Variety (예능) styles carry most of the jokes; mood styles stay quiet. Unit 5 swaps in bundled OFL fonts.
const SANS = '"Apple SD Gothic Neo", "Noto Sans KR", sans-serif';
const SERIF = '"AppleMyungjo", "Nanum Myeongjo", serif';
const SPEAKER_COLORS = ['#ffe14d', '#7fe0ff', '#ff9ec7', '#b6f36b'];

const POSITIONS: Record<string, CSSProperties> = {
  bottom: {left: 0, right: 0, bottom: 80, justifyContent: 'center'},
  top: {left: 0, right: 0, top: 70, justifyContent: 'center'},
  center: {left: 0, right: 0, top: 420, justifyContent: 'center'},
  upper_left: {left: 70, top: 60},
  upper_right: {right: 70, top: 140},
  lower_left: {left: 70, bottom: 120},
  lower_right: {right: 70, bottom: 120},
};

const outline = (color: string, width: number): CSSProperties => ({
  WebkitTextStroke: `${width}px ${color}`, paintOrder: 'stroke fill',
});

const speakerColor = (speaker?: string | null) => {
  if (!speaker) return '#ffffff';
  let hash = 0;
  for (const char of speaker) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return SPEAKER_COLORS[hash % SPEAKER_COLORS.length];
};

export const Caption = ({cue}: {cue: CaptionCue}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({frame, fps, config: {damping: 11, stiffness: 180}});
  const fade = interpolate(frame, [0, 8, cue.duration - 8, cue.duration], [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const wrap: CSSProperties = {position: 'absolute', display: 'flex', ...(POSITIONS[cue.position] ?? POSITIONS.bottom)};
  let style: CSSProperties;
  switch (cue.kind) {
    case 'variety':
      style = {fontFamily: SANS, fontSize: 92, fontWeight: 900, color: speakerColor(cue.speaker),
        ...outline('#111', 14), transform: `scale(${0.6 + 0.4 * pop})`, letterSpacing: -2};
      break;
    case 'situation':
      style = {fontFamily: SANS, fontSize: 44, fontWeight: 800, color: '#2b2100', background: '#ffd84d',
        padding: '10px 22px', borderRadius: 14, border: '4px solid #2b2100',
        transform: `translateY(${(1 - pop) * -30}px)`};
      break;
    case 'sfx_text':
      style = {fontFamily: SANS, fontSize: 120, fontWeight: 900, color: '#ff3b3b', ...outline('#fff', 12),
        transform: `rotate(-10deg) scale(${0.3 + 0.7 * pop})`};
      break;
    case 'inner_voice':
      style = {fontFamily: SANS, fontSize: 58, fontWeight: 700, color: '#bfe3ff', ...outline('#0b2540', 10),
        opacity: fade, fontStyle: 'italic'};
      break;
    case 'mood':
      style = {fontFamily: SERIF, fontSize: 52, fontWeight: 400, color: '#fffaf0', opacity: fade,
        textShadow: '0 2px 12px rgba(0,0,0,0.55)', letterSpacing: 2};
      break;
    case 'place':
      style = {fontFamily: SERIF, fontSize: 40, color: '#fffaf0', opacity: fade, borderLeft: '4px solid #fffaf0',
        paddingLeft: 18, textShadow: '0 2px 10px rgba(0,0,0,0.5)'};
      break;
    default:
      style = {fontFamily: SANS, fontSize: 56, fontWeight: 700, color: speakerColor(cue.speaker), ...outline('#111', 10)};
  }
  return (
    <div style={wrap}>
      <div style={{...style, whiteSpace: 'pre-wrap', textAlign: 'center', maxWidth: 1600}}>{cue.text}</div>
    </div>
  );
};
