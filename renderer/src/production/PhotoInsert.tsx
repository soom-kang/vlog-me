import {AbsoluteFill, Easing, Img, interpolate, staticFile, useCurrentFrame} from 'remotion';

// A photo taken at the place, pinned over the running video like a print on a scrapbook page.
export type PhotoInsertCue = {id: string; from: number; duration: number; position: 'left' | 'right'; tilt?: number};

const ENTER = 14;
const EXIT = 10;
const PHOTO_HEIGHT = 500;
const SIDE_MARGIN = 130;
const TOP = 190;

export const PhotoInsert = ({cue, src}: {cue: PhotoInsertCue; src: string}) => {
  const frame = useCurrentFrame();
  const tilt = cue.tilt ?? 0;
  const out = Math.max(ENTER, cue.duration - EXIT);
  const enter = interpolate(frame, [0, ENTER], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
    easing: Easing.out(Easing.back(1.4))});
  const exit = interpolate(frame, [out, cue.duration], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
    easing: Easing.in(Easing.cubic)});
  const opacity = Math.min(1, enter * 1.6) * (1 - exit);
  const lift = (1 - enter) * 70 - exit * 30;
  const scale = 0.9 + 0.1 * enter - 0.04 * exit;
  const rotate = tilt + (1 - enter) * (tilt >= 0 ? 7 : -7);
  // The print itself stays still; only the picture inside drifts, so the card reads as a physical photo.
  const drift = interpolate(frame, [0, cue.duration], [1, 1.05]);
  const side = cue.position === 'left' ? {left: SIDE_MARGIN} : {right: SIDE_MARGIN};
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <div style={{position: 'absolute', top: TOP, ...side, opacity,
        transform: `translateY(${lift}px) rotate(${rotate}deg) scale(${scale})`, transformOrigin: '50% 30%'}}>
        <div style={{background: '#fbf8f1', padding: '16px 16px 62px', borderRadius: 4,
          boxShadow: '0 28px 60px rgba(0,0,0,0.42), 0 6px 16px rgba(0,0,0,0.28)'}}>
          <div style={{height: PHOTO_HEIGHT, overflow: 'hidden', background: '#ddd'}}>
            <Img src={staticFile(src)} style={{height: PHOTO_HEIGHT, width: 'auto', display: 'block',
              transform: `scale(${drift})`}} />
          </div>
        </div>
        <div style={{position: 'absolute', top: -18, left: '50%', width: 132, height: 38, marginLeft: -66,
          background: 'rgba(238, 226, 196, 0.82)', transform: `rotate(${-tilt * 0.6 - 3}deg)`,
          boxShadow: '0 2px 6px rgba(0,0,0,0.12)'}} />
      </div>
    </AbsoluteFill>
  );
};
