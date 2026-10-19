import {AbsoluteFill, Composition, Sequence} from 'remotion';
import {Caption} from './Captions';
import registry from './presets.json';

// One cell per preset so the 80/20 caption system can be reviewed at a glance.
const SAMPLES: Record<string, string> = {
  variety: '결국 원점', situation: '같은 골목 3바퀴째', sfx_text: '띠용?!', inner_voice: '(기억력 테스트 실패)',
  dialogue: '여기 아까 왔던 데 아니야?', mood: '그래도 바람은 좋았다', place: '제주 · 협재 해변',
};
const POSITION: Record<string, string> = {situation: 'upper_left', sfx_text: 'upper_right', place: 'lower_left'};
const BACKGROUNDS = ['#4a6d7c', '#7c5a4a', '#4f7c4a', '#6b4a7c'];

const cells = Object.entries(registry.kinds).flatMap(([kind, spec]) =>
  spec.presets.map((preset) => ({kind, preset, group: spec.group})));
const COLUMNS = 2;
const SCALE = 1 / COLUMNS;

export const CaptionGallery = () => (
  <AbsoluteFill style={{backgroundColor: '#111'}}>
    {cells.map((cell, index) => (
      <div key={cell.preset} style={{position: 'absolute', width: 1920, height: 1080, overflow: 'hidden',
        left: (index % COLUMNS) * 960, top: Math.floor(index / COLUMNS) * 540,
        transform: `scale(${SCALE})`, transformOrigin: 'top left', background: BACKGROUNDS[(index + Math.floor(index / COLUMNS)) % BACKGROUNDS.length]}}>
        <Sequence from={0} durationInFrames={90} layout="none">
          <Caption cue={{id: cell.preset, kind: cell.kind, preset: cell.preset, text: SAMPLES[cell.kind],
            position: POSITION[cell.kind] ?? 'bottom', speaker: null, from: 0, duration: 90}} />
        </Sequence>
        <div style={{position: 'absolute', right: 40, top: 960, fontSize: 48, color: 'rgba(255,255,255,0.7)',
          fontFamily: 'sans-serif'}}>{`${cell.group} · ${cell.kind} · ${cell.preset}`}</div>
      </div>
    ))}
  </AbsoluteFill>
);

export const GalleryComposition = () => (
  <Composition id="CaptionGallery" component={CaptionGallery} durationInFrames={90} fps={30} width={1920}
    height={Math.ceil(cells.length / COLUMNS) * 540} />
);
