import {AbsoluteFill, Composition, Img, Sequence, staticFile} from 'remotion';
import {Audio, Video} from '@remotion/media';
import {gainAt} from './gain.mjs';
import {CandidateComposition} from './production/CandidatePreview';
import {GalleryComposition} from './production/CaptionGallery';
import {LookGalleryComposition} from './production/LookGallery';
import {ProductionComposition} from './production/ProductionTimeline';

type Interval = {id: string; from: number; duration: number};
type Timeline = {
  fps: number; width: number; height: number; duration_frames: number;
  clips: (Interval & {asset: string; trim?: number})[];
  audio: (Interval & {asset: string; trim?: number; gain_db: number[][]})[];
  captions: (Interval & {text: string; kind: string})[];
};
type Props = {timeline: Timeline; assets: Record<string, {file: string; kind: string}>};

export const TimelineVideo = ({timeline, assets}: Props) => (
  <AbsoluteFill style={{backgroundColor: '#18242c', fontFamily: 'Apple SD Gothic Neo, sans-serif'}}>
    {timeline.clips.map((clip) => (
      <Sequence key={clip.id} from={clip.from} durationInFrames={clip.duration} name={clip.id}>
        {assets[clip.asset].kind === 'video' ? (
          <Video src={staticFile(assets[clip.asset].file)} trimBefore={clip.trim ?? 0} muted
            style={{width: '100%', height: '100%'}} objectFit="contain" />
        ) : (
          <Img src={staticFile(assets[clip.asset].file)} style={{width: '100%', height: '100%', objectFit: 'contain'}} />
        )}
      </Sequence>
    ))}
    {timeline.audio.map((cue) => (
      <Sequence key={cue.id} from={cue.from} durationInFrames={cue.duration} name={cue.id}>
        <Audio src={staticFile(assets[cue.asset].file)} trimBefore={cue.trim ?? 0}
          volume={(frame) => gainAt(frame, cue.gain_db)} />
      </Sequence>
    ))}
    <div style={{position: 'absolute', top: 24, left: 32, padding: '8px 14px', color: 'white', background: '#18242cdd', fontSize: 22}}>
      vlog-me · SYNTHETIC SETUP · 실제 촬영본 아님
    </div>
    {timeline.captions.map((cue) => (
      <Sequence key={cue.id} from={cue.from} durationInFrames={cue.duration} name={cue.id}>
        <div style={{position: 'absolute', bottom: 72, left: 64, right: 64, textAlign: 'center',
          color: '#fff4bd', fontSize: 46, fontWeight: 800, textShadow: '0 3px 6px #000', whiteSpace: 'pre-wrap'}}>
          {cue.text}
        </div>
      </Sequence>
    ))}
  </AbsoluteFill>
);

// One data-driven template: edit timeline.json, not per-clip JSX in Studio.
export const Root = () => (
  <>
  <Composition id="VlogSetup" component={TimelineVideo} durationInFrames={30} fps={30} width={1280} height={720}
    defaultProps={{timeline: {fps: 30, width: 1280, height: 720, duration_frames: 30, clips: [], audio: [], captions: []}, assets: {}}}
    calculateMetadata={({props}) => ({durationInFrames: props.timeline.duration_frames, fps: props.timeline.fps,
      width: props.timeline.width, height: props.timeline.height})} />
  <CandidateComposition />
  <GalleryComposition />
  <LookGalleryComposition />
  <ProductionComposition />
  </>
);
