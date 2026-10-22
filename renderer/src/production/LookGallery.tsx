import {AbsoluteFill, Composition, Sequence} from 'remotion';
import {Caption} from './Captions';
import {EffectOverlay} from './Effects';
import {LookOverlay, lookFilter, type LookSpec} from './Look';
import registry from './presets.json';

const CELLS: {label: string; look?: LookSpec; leak?: boolean}[] = [
  {label: 'none'},
  {label: 'warm', look: {grade: 'warm'}},
  {label: 'faded', look: {grade: 'faded'}},
  {label: 'film', look: {grade: 'film'}},
  {label: 'recommended', look: {...registry.look.recommended, grade: 'warm'}},
  {label: 'letterbox 2.39', look: {letterbox: 2.39}},
  {label: 'vignette 0.4 + grain 0.2', look: {vignette: 0.4, grain: 0.2}},
  {label: 'light_leak', leak: true},
];

// Synthetic scenery only; look comparisons require no source files or network assets.
export const LookGallery = () => (
  <AbsoluteFill style={{background: '#111'}}>
    {CELLS.map((cell, index) => (
      <div key={cell.label} style={{position: 'absolute', width: 1920, height: 1080, overflow: 'hidden',
        left: index % 2 * 960, top: Math.floor(index / 2) * 540, transform: 'scale(0.5)', transformOrigin: 'top left'}}>
        <AbsoluteFill style={{filter: lookFilter(cell.look)}}>
          <AbsoluteFill style={{background: 'linear-gradient(#8aaec7 0%, #e5cfac 53%, #547b88 54%, #284b60 100%)'}} />
          <div style={{position: 'absolute', left: 1320, top: 220, width: 180, height: 180, borderRadius: '50%', background: '#fff1c8'}} />
        </AbsoluteFill>
        {cell.leak ? <Sequence from={-15} durationInFrames={90} layout="none">
          <EffectOverlay cue={{id: 'gallery-leak', type: 'light_leak', from: 0, duration: 90, strength: 1}} />
        </Sequence> : null}
        <LookOverlay look={cell.look} />
        <Sequence from={-60} durationInFrames={180} layout="none">
          <Caption cue={{id: cell.label, kind: 'mood', preset: 'bilingual', text: '그래도 바람은 좋았다',
            sub: 'a slow day', position: 'center', from: 0, duration: 180}} />
        </Sequence>
        <div style={{position: 'absolute', right: 40, bottom: 40, color: '#fff', background: 'rgba(0,0,0,0.5)',
          padding: '8px 16px', fontFamily: 'sans-serif', fontSize: 36}}>{cell.label}</div>
      </div>
    ))}
  </AbsoluteFill>
);

export const LookGalleryComposition = () => (
  <Composition id="LookGallery" component={LookGallery} durationInFrames={90} fps={30} width={1920} height={2160} />
);
