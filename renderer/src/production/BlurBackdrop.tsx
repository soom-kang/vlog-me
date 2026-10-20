import {AbsoluteFill, Img, staticFile} from 'remotion';
import {Video} from '@remotion/media';

// Fills the side bars of vertical photos and clips with a heavily blurred copy of the same picture,
// so the frame keeps the shot's colours instead of showing black.
const WIDE = 16 / 9;
const LOOK = {filter: 'blur(46px) brightness(0.72) saturate(1.2)'};

export const needsBackdrop = (aspect?: number) => aspect !== undefined && Math.abs(aspect - WIDE) > 0.05;

export const BlurBackdrop = ({kind, src, aspect, trimBefore = 0, playbackRate = 1}: {
  kind: 'video' | 'image'; src: string; aspect?: number; trimBefore?: number; playbackRate?: number;
}) => {
  if (kind === 'image') {
    return (
      <AbsoluteFill style={{overflow: 'hidden'}}>
        <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover', transform: 'scale(1.15)', ...LOOK}} />
      </AbsoluteFill>
    );
  }
  if (!needsBackdrop(aspect)) return null;
  // Video proxies are padded to 16:9, so scale until the picture itself spans the frame, then blur.
  const scale = Math.max(WIDE / (aspect as number), (aspect as number) / WIDE) * 1.12;
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <AbsoluteFill style={{transform: `scale(${scale})`, ...LOOK}}>
        <Video src={staticFile(src)} trimBefore={trimBefore} playbackRate={playbackRate} muted
          style={{width: '100%', height: '100%'}} objectFit="contain" />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
