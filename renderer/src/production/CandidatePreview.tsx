import {AbsoluteFill, Composition, Img, Sequence, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {Audio, Video} from '@remotion/media';
import {gainAt} from '../gain.mjs';
import {BlurBackdrop} from './BlurBackdrop';
import {Caption, type CaptionCue} from './Captions';
import {EffectOverlay, effectTransform, type EffectCue} from './Effects';
import {PhotoInsert, type PhotoInsertCue} from './PhotoInsert';
import {PhotoStack, type PhotoStackCue} from './PhotoStack';

type Segment = {src: string; trimBefore: number; frames: number; playbackRate: number; gain?: number[][]; aspect?: number};
type AudioCue = {id: string; src: string; from: number; duration: number; gain: number[][]; in?: number};
export type CandidateProps = {
  kind: 'video' | 'image'; segments: Segment[]; zoom: number; captions: CaptionCue[]; audio?: AudioCue[];
  overlays?: ((PhotoInsertCue & {style?: undefined; src: string}) | (PhotoStackCue & {style: 'stack'; srcs: string[]}))[];
  effects?: EffectCue[];
  durationInFrames: number; keyFrame: number;
};

const Zoomed = ({zoom, durationInFrames, children}: {zoom: number; durationInFrames: number; children: React.ReactNode}) => {
  const frame = useCurrentFrame();
  // Photos drift from 1x to the planned zoom; video keeps a steady punch-in.
  const scale = interpolate(frame, [0, durationInFrames], [1, zoom], {extrapolateRight: 'clamp'});
  return <AbsoluteFill style={{transform: `scale(${scale})`}}>{children}</AbsoluteFill>;
};

export const CandidatePreview = ({kind, segments, zoom, captions, audio = [], overlays = [], effects = [],
  durationInFrames}: CandidateProps) => {
  const frame = useCurrentFrame();
  let offset = 0;
  return (
    <AbsoluteFill style={{backgroundColor: 'black'}}>
      <AbsoluteFill style={{transform: effectTransform(frame, effects)}}>
      {segments.map((segment, index) => {
        const from = offset;
        offset += segment.frames;
        return (
          <Sequence key={index} from={from} durationInFrames={segment.frames} name={`cut-${index}`}>
            {kind === 'video' ? (
              <>
                <BlurBackdrop kind="video" src={segment.src} aspect={segment.aspect} trimBefore={segment.trimBefore}
                  playbackRate={segment.playbackRate} />
                <AbsoluteFill style={{transform: `scale(${zoom})`}}>
                  <Video src={staticFile(segment.src)} trimBefore={segment.trimBefore} playbackRate={segment.playbackRate}
                    volume={segment.gain ? (f) => gainAt(f, segment.gain as number[][]) : 1}
                    style={{width: '100%', height: '100%'}} objectFit="contain" />
                </AbsoluteFill>
              </>
            ) : (
              <>
                <BlurBackdrop kind="image" src={segment.src} aspect={segment.aspect} />
                <Zoomed zoom={zoom} durationInFrames={durationInFrames}>
                  <Img src={staticFile(segment.src)} style={{width: '100%', height: '100%', objectFit: 'contain'}} />
                </Zoomed>
              </>
            )}
          </Sequence>
        );
      })}
      </AbsoluteFill>
      {effects.map((cue) => (
        <Sequence key={cue.id} from={cue.from} durationInFrames={cue.duration} name={cue.id}>
          <EffectOverlay cue={cue} />
        </Sequence>
      ))}
      {audio.map((cue) => (
        // Library BGM/SFX from run/audio; the BGM envelope already ducks under speech.
        <Sequence key={cue.id} from={cue.from} durationInFrames={cue.duration} name={cue.id}>
          <Audio src={staticFile(cue.src)} trimBefore={cue.in ?? 0} volume={(frame) => gainAt(frame, cue.gain)} />
        </Sequence>
      ))}
      {overlays.map((cue) => (
        <Sequence key={cue.id} from={cue.from} durationInFrames={cue.duration} name={cue.id}>
          {cue.style === 'stack' ? <PhotoStack cue={cue} srcs={cue.srcs} /> : <PhotoInsert cue={cue} src={cue.src} />}
        </Sequence>
      ))}
      {captions.map((cue) => (
        <Sequence key={cue.id} from={cue.from} durationInFrames={cue.duration} name={cue.id}>
          <Caption cue={cue} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};

const EMPTY: CandidateProps = {kind: 'image', segments: [], zoom: 1, captions: [], audio: [], overlays: [], effects: [], durationInFrames: 30,
  keyFrame: 0};

export const CandidateComposition = () => (
  <Composition id="CandidatePreview" component={CandidatePreview} durationInFrames={30} fps={30} width={1920} height={1080}
    defaultProps={EMPTY}
    calculateMetadata={({props}) => ({durationInFrames: props.durationInFrames})} />
);
