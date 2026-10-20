import {AbsoluteFill, Composition, Img, Sequence, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {Audio, Video} from '@remotion/media';
import {gainAt} from '../gain.mjs';
import {Caption, type CaptionCue} from './Captions';
import {EffectOverlay, effectTransform, type EffectCue} from './Effects';
import {PhotoInsert, type PhotoInsertCue} from './PhotoInsert';
import {PhotoStack, type PhotoStackCue} from './PhotoStack';

// Renders timeline v2 (scripts/production.py validates it before every render).
type Clip = {id: string; source: string; from: number; duration: number; in?: number; speed?: number; zoom?: number;
  tag: string; transition?: string};
type AudioCue = {id: string; kind: string; clip?: string; source?: string; from: number; duration: number; in?: number;
  gain_db: number[][]};
type Asset = {src: string; kind: 'video' | 'image' | 'audio'};
export type ProductionProps = {
  timeline: {fps: number; width: number; height: number; duration_frames: number; clips: Clip[]; audio: AudioCue[];
    captions: CaptionCue[]; effects?: EffectCue[];
    overlays?: ((PhotoInsertCue & {style?: undefined; source: string}) | (PhotoStackCue & {style: 'stack'; sources: string[]}))[]};
  assets: Record<string, Asset>;
};

const FADE = 10;

const ClipVisual = ({clip, asset}: {clip: Clip; asset: Asset}) => {
  const frame = useCurrentFrame();
  const zoom = clip.zoom ?? 1;
  const opacity = clip.transition === 'fade' ? interpolate(frame, [0, FADE], [0, 1], {extrapolateRight: 'clamp'}) : 1;
  if (asset.kind === 'image') {
    // Photos drift slowly toward the planned zoom.
    const scale = interpolate(frame, [0, clip.duration], [1, zoom], {extrapolateRight: 'clamp'});
    return (
      <AbsoluteFill style={{opacity, transform: `scale(${scale})`}}>
        <Img src={staticFile(asset.src)} style={{width: '100%', height: '100%', objectFit: 'contain'}} />
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{opacity, transform: `scale(${zoom})`}}>
      <Video src={staticFile(asset.src)} trimBefore={clip.in ?? 0} playbackRate={clip.speed ?? 1} muted
        style={{width: '100%', height: '100%'}} objectFit="contain" />
    </AbsoluteFill>
  );
};

export const ProductionTimeline = ({timeline, assets}: ProductionProps) => {
  const frame = useCurrentFrame();
  const clips = new Map(timeline.clips.map((clip) => [clip.id, clip]));
  const effects = timeline.effects ?? [];
  return (
    <AbsoluteFill style={{backgroundColor: 'black'}}>
      <AbsoluteFill style={{transform: effectTransform(frame, effects)}}>
        {timeline.clips.map((clip) => (
          <Sequence key={clip.id} from={clip.from} durationInFrames={clip.duration} name={clip.id}>
            <ClipVisual clip={clip} asset={assets[clip.source]} />
          </Sequence>
        ))}
      </AbsoluteFill>
      {effects.map((cue) => (
        <Sequence key={cue.id} from={cue.from} durationInFrames={cue.duration} name={cue.id}>
          <EffectOverlay cue={cue} />
        </Sequence>
      ))}
      {timeline.audio.map((cue) => {
        // Original sound follows its clip's in-point and speed; BGM/SFX come from staged library files.
        const clip = cue.kind === 'original' && cue.clip ? clips.get(cue.clip) : undefined;
        const asset = assets[clip ? clip.source : cue.source ?? ''];
        return (
          <Sequence key={cue.id} from={cue.from} durationInFrames={cue.duration} name={cue.id}>
            <Audio src={staticFile(asset.src)} trimBefore={clip ? clip.in ?? 0 : cue.in ?? 0}
              playbackRate={clip ? clip.speed ?? 1 : 1} volume={(frame) => gainAt(frame, cue.gain_db)} />
          </Sequence>
        );
      })}
      {(timeline.overlays ?? []).map((cue) => (
        <Sequence key={cue.id} from={cue.from} durationInFrames={cue.duration} name={cue.id}>
          {cue.style === 'stack'
            ? <PhotoStack cue={cue} srcs={cue.sources.map((name) => assets[name].src)} />
            : <PhotoInsert cue={cue} src={assets[cue.source].src} />}
        </Sequence>
      ))}
      {timeline.captions.map((cue) => (
        <Sequence key={cue.id} from={cue.from} durationInFrames={cue.duration} name={cue.id}>
          <Caption cue={cue} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};

const EMPTY: ProductionProps = {
  timeline: {fps: 30, width: 1920, height: 1080, duration_frames: 30, clips: [], audio: [], captions: []}, assets: {},
};

export const ProductionComposition = () => (
  <Composition id="ProductionTimeline" component={ProductionTimeline} durationInFrames={30} fps={30} width={1920} height={1080}
    defaultProps={EMPTY}
    calculateMetadata={({props}) => ({durationInFrames: props.timeline.duration_frames, fps: props.timeline.fps,
      width: props.timeline.width, height: props.timeline.height})} />
);
