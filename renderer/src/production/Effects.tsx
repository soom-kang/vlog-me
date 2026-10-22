import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {lightLeakOpacity} from './mood.mjs';

// Short camera effects: variety (punch_zoom, shake, flash, speedlines) and mood (light_leak).
export type EffectCue = {id: string; type: 'punch_zoom' | 'shake' | 'flash' | 'speedlines' | 'light_leak'; from: number; duration: number;
  strength?: number};

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

/** CSS transform for the picture at a global frame, combining every active punch_zoom and shake. */
export const effectTransform = (frame: number, effects: EffectCue[]) => {
  let scale = 1;
  let x = 0;
  let y = 0;
  for (const fx of effects) {
    const local = frame - fx.from;
    if (local < 0 || local >= fx.duration) continue;
    const strength = fx.strength ?? 1;
    if (fx.type === 'punch_zoom') {
      const amount = interpolate(local, [0, 4, Math.max(5, fx.duration - 6), fx.duration], [0, 1, 1, 0], clamp);
      scale *= 1 + 0.22 * strength * amount;
    } else if (fx.type === 'shake') {
      const decay = 1 - local / fx.duration;
      x += Math.sin(local * 2.7) * 16 * strength * decay;
      y += Math.cos(local * 3.3) * 11 * strength * decay;
    }
  }
  return `translate(${x}px, ${y}px) scale(${scale})`;
};

export const EffectOverlay = ({cue}: {cue: EffectCue}) => {
  const frame = useCurrentFrame();
  const strength = cue.strength ?? 1;
  if (cue.type === 'light_leak') {
    const left = interpolate(frame, [0, cue.duration], [-30, 110], clamp);
    return <AbsoluteFill style={{pointerEvents: 'none', overflow: 'hidden', mixBlendMode: 'screen',
      opacity: lightLeakOpacity(frame, cue.duration, strength)}}>
      <div style={{position: 'absolute', top: '-20%', bottom: '-20%', left: `${left}%`, width: '80%',
        background: 'radial-gradient(ellipse at 30% 35%, rgba(255,170,90,0.9), transparent 65%), radial-gradient(ellipse at 60% 75%, rgba(255,120,160,0.6), transparent 65%)'}} />
    </AbsoluteFill>;
  }
  if (cue.type === 'flash') {
    const opacity = interpolate(frame, [0, 2, Math.min(cue.duration, 10)], [0, 0.9 * Math.min(1, strength), 0], clamp);
    return <AbsoluteFill style={{background: '#ffffff', opacity, pointerEvents: 'none'}} />;
  }
  if (cue.type === 'speedlines') {
    const fade = interpolate(frame, [0, 4, cue.duration - 6, cue.duration], [0, 1, 1, 0], clamp);
    const count = Math.round(18 * strength);
    return (
      <AbsoluteFill style={{pointerEvents: 'none', opacity: fade * 0.75}}>
        {Array.from({length: count}, (_, i) => {
          const top = ((i * 97) % 1000) / 1000 * 1080;
          const length = 260 + ((i * 53) % 7) * 70;
          const speed = 70 + ((i * 31) % 5) * 25;
          const left = 1920 - ((frame * speed + i * 211) % (1920 + length));
          return <div key={i} style={{position: 'absolute', top, left, width: length, height: 3 + (i % 3),
            borderRadius: 3, background: 'linear-gradient(90deg, rgba(255,255,255,0), rgba(255,255,255,0.95))'}} />;
        })}
      </AbsoluteFill>
    );
  }
  return null;
};
