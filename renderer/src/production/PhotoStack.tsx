import {AbsoluteFill, Easing, Img, interpolate, staticFile, useCurrentFrame} from 'remotion';

// A burst of prints dropping onto a pile, one every `interval` frames ("찰칵찰칵" moments).
export type PhotoStackCue = {id: string; from: number; duration: number; interval: number;
  position: 'left' | 'right' | 'center'};

const DROP = 9;
const EXIT = 10;
const HEIGHT = 430;
const ANCHOR: Record<string, number> = {left: 520, center: 960, right: 1400};

// Deterministic scatter so a re-render lands every print in the same place.
const scatter = (index: number) => {
  const seed = Math.sin((index + 1) * 12.9898) * 43758.5453;
  const r = seed - Math.floor(seed);
  return {rotate: (r - 0.5) * 22, dx: (((index * 37) % 9) - 4) * 26, dy: (((index * 53) % 7) - 3) * 16};
};

export const PhotoStack = ({cue, srcs}: {cue: PhotoStackCue; srcs: string[]}) => {
  const frame = useCurrentFrame();
  const leave = interpolate(frame, [cue.duration - EXIT, cue.duration], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
    easing: Easing.in(Easing.cubic)});
  return (
    <AbsoluteFill style={{pointerEvents: 'none', opacity: 1 - leave}}>
      {srcs.map((src, index) => {
        const start = index * cue.interval;
        if (frame < start) return null;
        const t = interpolate(frame, [start, start + DROP], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
          easing: Easing.out(Easing.back(1.6))});
        const {rotate, dx, dy} = scatter(index);
        const flash = interpolate(frame, [start, start + 4], [0.85, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
        return (
          <div key={index} style={{position: 'absolute', left: ANCHOR[cue.position] + dx, top: 300 + dy,
            transform: `translate(-50%, ${(1 - t) * -160}px) rotate(${rotate + (1 - t) * 18}deg) scale(${1.25 - 0.25 * t})`,
            opacity: Math.min(1, t * 2), zIndex: index}}>
            <div style={{background: '#fbf8f1', padding: '14px 14px 48px', borderRadius: 3,
              boxShadow: '0 22px 50px rgba(0,0,0,0.45), 0 4px 12px rgba(0,0,0,0.3)', position: 'relative'}}>
              <Img src={staticFile(src)} style={{height: HEIGHT, width: 'auto', display: 'block'}} />
              <div style={{position: 'absolute', inset: 14, bottom: 48, background: '#ffffff', opacity: flash}} />
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
