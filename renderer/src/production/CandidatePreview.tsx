import {AbsoluteFill, Composition, Img, Sequence, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {Video} from '@remotion/media';
import {Caption, type CaptionCue} from './Captions';

type Segment = {src: string; trimBefore: number; frames: number; playbackRate: number};
export type CandidateProps = {
  kind: 'video' | 'image'; segments: Segment[]; zoom: number; captions: CaptionCue[];
  durationInFrames: number; keyFrame: number;
};

const Zoomed = ({zoom, durationInFrames, children}: {zoom: number; durationInFrames: number; children: React.ReactNode}) => {
  const frame = useCurrentFrame();
  // Photos drift from 1x to the planned zoom; video keeps a steady punch-in.
  const scale = interpolate(frame, [0, durationInFrames], [1, zoom], {extrapolateRight: 'clamp'});
  return <AbsoluteFill style={{transform: `scale(${scale})`}}>{children}</AbsoluteFill>;
};

export const CandidatePreview = ({kind, segments, zoom, captions, durationInFrames}: CandidateProps) => {
  let offset = 0;
  return (
    <AbsoluteFill style={{backgroundColor: 'black'}}>
      {segments.map((segment, index) => {
        const from = offset;
        offset += segment.frames;
        return (
          <Sequence key={index} from={from} durationInFrames={segment.frames} name={`cut-${index}`}>
            {kind === 'video' ? (
              <AbsoluteFill style={{transform: `scale(${zoom})`}}>
                <Video src={staticFile(segment.src)} trimBefore={segment.trimBefore} playbackRate={segment.playbackRate}
                  style={{width: '100%', height: '100%'}} objectFit="contain" />
              </AbsoluteFill>
            ) : (
              <Zoomed zoom={zoom} durationInFrames={durationInFrames}>
                <Img src={staticFile(segment.src)} style={{width: '100%', height: '100%', objectFit: 'contain'}} />
              </Zoomed>
            )}
          </Sequence>
        );
      })}
      {captions.map((cue) => (
        <Sequence key={cue.id} from={cue.from} durationInFrames={cue.duration} name={cue.id}>
          <Caption cue={cue} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};

const EMPTY: CandidateProps = {kind: 'image', segments: [], zoom: 1, captions: [], durationInFrames: 30, keyFrame: 0};

export const CandidateComposition = () => (
  <Composition id="CandidatePreview" component={CandidatePreview} durationInFrames={30} fps={30} width={1920} height={1080}
    defaultProps={EMPTY}
    calculateMetadata={({props}) => ({durationInFrames: props.durationInFrames})} />
);
