import {AbsoluteFill, Composition, Sequence} from 'remotion';
import {Caption} from './Captions';
import registry from './presets.json';

// One cell per preset so the mood-first caption system can be reviewed at a glance.
const SAMPLES: Record<string, string> = {
  variety: '결국 원점', situation: '같은 골목 3바퀴째', sfx_text: '띠용?!', inner_voice: '(기억력 테스트 실패)',
  narration: '오늘은 조금 천천히 걷기로 했다\n바람이 먼저 와 있었다\n그걸로 충분했다',
  dialogue: '여기 아까 왔던 데 아니야?', mood: '그래도 바람은 좋았다', place: '제주 · 협재 해변',
};
const SUBS: Record<string, string> = {mood: 'golden hour', place: 'PHU QUOC', narration: 'a slow day'};
const POSITION: Record<string, string> = {narration: 'lower_left', situation: 'upper_left', sfx_text: 'upper_right', place: 'lower_left', mood: 'center'};
// Reference-style (구어체) presets get spoken-tone samples and their recommended positions.
const PRESET_SAMPLES: Record<string, string> = {
  talk: '그나저나 여기 노을이 진짜 미쳤어요..', 'talk-note': '오일은 직접 고를 수 있어요\n저는 코코넛으로!',
  'talk-mood': '바람 진짜 많이 불던 날', 'place-tiny': '살린다 리조트', 'pop-word': '미쳐',
};
const PRESET_SUBS: Record<string, string | null> = {'talk-note': null, 'talk-mood': null, 'place-tiny': 'PHU QUOC · 10:38'};
const PRESET_POSITION: Record<string, string> = {'talk-note': 'bottom', 'talk-mood': 'bottom', 'place-tiny': 'upper_left', 'pop-word': 'center'};
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
        {/* At still frame 30, local frame 150 shows every narration line before fade-out. */}
        <Sequence from={-120} durationInFrames={180} layout="none">
          <Caption cue={{id: cell.preset, kind: cell.kind, preset: cell.preset,
            text: PRESET_SAMPLES[cell.preset] ?? SAMPLES[cell.kind],
            position: PRESET_POSITION[cell.preset] ?? POSITION[cell.kind] ?? 'bottom', speaker: null,
            sub: cell.preset in PRESET_SUBS ? PRESET_SUBS[cell.preset] : SUBS[cell.kind] ?? null, from: 0, duration: 180}} />
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
