import {useId} from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {gradeFilter, letterboxBar} from './mood.mjs';

export type LookSpec = {grade?: 'none' | 'warm' | 'faded' | 'film'; grade_strength?: number;
  grain?: number; vignette?: number; letterbox?: number | null};

export const lookFilter = (look?: LookSpec) => look ? gradeFilter(look.grade ?? 'none', look.grade_strength ?? 0.6).filter : 'none';

// This layer sits below captions; frame-based grain remains identical on chunked renders.
export const LookOverlay = ({look}: {look?: LookSpec}) => {
  const frame = useCurrentFrame();
  const noiseId = useId();
  if (!look) return null;
  const {tint} = gradeFilter(look.grade ?? 'none', look.grade_strength ?? 0.6);
  const grain = look.grain ?? 0;
  const vignette = look.vignette ?? 0;
  const bar = look.letterbox ? letterboxBar(look.letterbox) : 0;
  return <AbsoluteFill style={{pointerEvents: 'none'}}>
    {tint ? <AbsoluteFill style={{background: tint.color, mixBlendMode: tint.blend}} /> : null}
    {vignette > 0 ? <AbsoluteFill style={{background: `radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,${vignette}) 100%)`}} /> : null}
    {grain > 0 ? <svg width={960} height={540} viewBox="0 0 960 540" style={{position: 'absolute', left: 0, top: 0,
      transform: 'scale(2)', transformOrigin: 'top left', mixBlendMode: 'overlay', opacity: grain}}>
      <defs><filter id={noiseId} x="0%" y="0%" width="100%" height="100%">
        <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={frame % 12} />
        <feColorMatrix type="saturate" values="0" />
      </filter></defs>
      <rect width="960" height="540" filter={`url(#${noiseId})`} />
    </svg> : null}
    {bar > 0 ? <>
      <div style={{position: 'absolute', top: 0, left: 0, right: 0, height: bar, background: 'black'}} />
      <div style={{position: 'absolute', bottom: 0, left: 0, right: 0, height: bar, background: 'black'}} />
    </> : null}
  </AbsoluteFill>;
};
