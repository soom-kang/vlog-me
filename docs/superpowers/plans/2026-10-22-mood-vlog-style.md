# 감성 브이로그 스타일(감성 90 · 예능 10) 구현 계획

- 날짜: 2026-10-22
- feature id: `mood-vlog-style`
- 실행: Orca coding worker(Codex)가 child worktree에서 진행합니다. 원본 미디어는 없고, 필요하지도 않습니다.
- 요청 요지: 자막·편집 분위기를 "예능 80 · 감성 20"에서 **감성 90 · 예능 10**으로 뒤집습니다. 풍경을 보여주며 대사 없이 자막만으로 이야기를 전하는 장면(내레이션·독백 자막)을 만들 수 있어야 하고, 가장 중요한 것은 감성 브이로그에 맞는 자막 스타일과 효과입니다. 이번에는 **환경 구성만** 합니다. 영상 편집·렌더는 하지 않습니다.

## 0. 원칙 (coding worker)

- `AGENTS.md`를 따릅니다. `sources/`, `work/`, `raw/`, `assets/audio/`, `.env*`는 읽지도 나열하지도 않습니다.
- `feature_list.json`, `progress.md`, `session-handoff.md`, `reports/`, `config/project.json`은 고치지 않습니다(coordinator 몫, 12절).
- `config/`의 phase·범위·권한 값(`phase`, `source_roots`, `use_subagents`, `audio_*`, `production_render`, `upload`, `external_processing`)은 바꾸지 않습니다. 이 계획은 `config/production.example.json`의 `editorial_direction`·`caption_style` 문자열만 바꿉니다.
- 폰트·음원·패키지를 내려받지 않습니다. `config/fonts-lock.json`의 7개 OFL 폰트만 씁니다.
- 렌더(영상·still·갤러리)를 실행하지 않습니다. 갤러리 still 생성은 병합 뒤 coordinator가 합니다(12절).
- 기존 kind·preset·필드는 지우지 않습니다. 기존 prod timeline이 그대로 검증을 통과해야 합니다(2절).
- 이 계획이 명시한 테스트 기대값 변경(5·6절의 비율 관련 assert)만 허용합니다. 그 밖의 assert·테스트를 지우거나 느슨하게 하지 않습니다.
- task마다 `./scripts/dev-check.sh`를 실행하고, task 단위로 로컬 커밋합니다(push 없음).

## 1. 레퍼런스 관찰

2026-10-22에 웹 검색과 기사·위키·인터뷰로 조사했습니다. 영상은 내려받거나 직접 보지 않았습니다. 채널 페이지와 영상 목록은 읽기 도구로 내용을 가져오지 못했습니다. **두 채널 모두 자막 폰트 이름, 자막 위치, 등장 타이밍, 영문 병기, 색보정, 그레인, 레터박스, 전환 방식은 어떤 출처에서도 확인하지 못했습니다.** 아래에서 "확인"은 출처에 적힌 내용이고, "추정"은 장르 관례에 근거한 판단입니다.

### 오눅 (@onuk)

| 관찰 | 근거 | 상태 |
| --- | --- | --- |
| 도쿄 직장인 시절 출근부터 퇴근까지의 일상(요리, 옷차림, 편의점, 점심, 쇼핑)으로 시작 | [비즈한국](https://bizhankook.com/articles/17229.html) | 확인 |
| "자극적이지 않고 편안할 뿐더러 잔잔한 생활소음이 ASMR 효과"를 줘 자기 전에 본다는 시청자가 많음. **생활소음(현장음)이 핵심** | [비즈한국](https://bizhankook.com/articles/17229.html) | 확인 |
| 인기 요인은 요리·패션·빈티지 인테리어 같은 감각. 편집 기법 서술은 없음 | [vling](https://vling.net/post/222025665852) | 확인 |
| 제목은 "~하는 브이로그.‧ 피부관리, 스낵틴 🥡"처럼 소문자 느낌과 기호를 섞음. 25분대 롱폼 | [sozai.app](https://sozai.app/transcripts/channel/onuk/) | 확인 |
| 대사보다 짧은 1인칭 독백 자막, 작은 글씨, 하단 배치, 긴 쇼트, 따뜻하거나 바랜 톤 | 장르 관례 | 추정 |

### 강민경 (@iammingki, 걍밍경)

| 관찰 | 근거 | 상태 |
| --- | --- | --- |
| 본인이 직접 편집. 편집 감각의 뿌리는 '무한도전'("예능의 편집점을 제 안에 쌓아오고") | [TV리포트 2022-10-30](https://tvreport.co.kr/star/article/162804/), [나무위키](https://namu.wiki/w/걍밍경) | 확인 |
| 인트로 하이라이트, 리드미컬한 박자 컷, 박자에 맞춘 줌 인·아웃, 표정 클로즈샷, 웃긴 쿠키 엔딩 | [고구마팜](https://gogumafarm.kr/?p=5571) | 확인 |
| 자막은 받아 적은 대사 자막이 가장 많고, 강조할 말만 색·크기·폰트를 바꿔 변주. 자막으로 표정을 강조하거나 행동을 설명 | [고구마팜](https://gogumafarm.kr/?p=5571) | 확인 |
| 레트로한 색감은 보정보다 카메라 기종에서 나옴(캐논 익서스 70, 캠코더 등). 주로 Sony a7c | [얼루어](https://www.allurekorea.com/?p=284619) | 확인 |
| 직접 만든 노래 '걍살자'를 오프닝·클로징에 자주 씀 | [나무위키](https://namu.wiki/w/걍밍경) | 확인 |

**해석:** 근거로 보면 오눅은 감성 쪽(생활소음, 잔잔함, 일상의 감각), 강민경은 예능 쪽(리듬 컷, 줌, 강조 대사 자막의 변주)에 가깝습니다. 이 계획은 감성 90을 오눅 계열 관찰과 장르 관례로, 예능 10을 강민경식 "강조할 말만 살짝 변주"로 해석합니다.

### 공통 감성 브이로그 관례

| 관찰 | 근거 | 상태 |
| --- | --- | --- |
| 명조 계열 폰트가 웹 예능·브이로그 자막에 자주 쓰임 | [산돌 폰트 추천](https://www.sandollcloud.com/font-recommendations/article/278) | 확인(일반론) |
| 한국 슬로우 리빙 브이로그는 말 대신 자막으로 설명하고, 인트로·아웃트로를 빼면 BGM 없이 생활소리나 정적을 두며, 따뜻한 색감과 느린 동작을 씀 | [Buro 24/7](https://www.buro247.my/culture/life/south-korean-slow-living-vloggers.html) | 확인(다른 채널 사례) |
| 하단 가운데 또는 좌하단의 작은 흰색 명조·손글씨 자막, 1인칭 일기체, 1–2줄씩 페이드, 영문 병기, 따뜻하거나 바랜 필름 톤, 가벼운 그레인, 컷 위주에 가끔 디졸브, 낮은 볼륨의 어쿠스틱·로파이 BGM과 생활소음 | 장르 관례 | 추정 |

**설계에 반영한 것:** 작은 명조(Gowun Batang) 자막과 넉넉한 줄 간격, 줄 단위로 차례로 나타나는 내레이션, 영문 세리프(Cormorant Garamond) 부제, 부드럽고 느린 페이드, 선택형 따뜻한/바랜 색감·그레인·비네트·레터박스·라이트 릭, 디졸브, 느린 줌, 그리고 사운드 가이드의 "현장음 우선" 강화. 폰트와 위치는 추정이 섞여 있으므로 **사용자가 실제 영상 캡처로 취향을 확인**해야 합니다(14절 남은 질문).

## 2. 핵심 결정

| 주제 | 결정 | 근거 |
| --- | --- | --- |
| 비율 키 | `presets.json`의 `target_variety_share`(0.8)를 **`target_mood_share`(0.9)로 바꿉니다**. `share_window`는 `[0.8, 1.0]`이며 감성 비율에 적용합니다. 별칭은 두지 않습니다 | 비율은 보고용이고 검증(`validate_timeline_v2`)에 쓰이지 않습니다. timeline에 저장되지 않으므로 기존 prod timeline 검증은 깨지지 않습니다. 이 키를 읽는 곳은 `production.caption_style_share` 하나뿐이라 이름을 의미에 맞게 바꾸는 비용이 작습니다 |
| 비율 계산 | 감성 = `group: "mood"`(`mood`·`place`·새 `narration`), 예능 = `group: "variety"`, `dialogue`는 제외. `caption_style_share`는 `mood_share`를 주 지표로 내고, 기존 `variety_share`도 함께 돌려줍니다(=1−mood_share) | 리포트 소비자(`review.py`, `assemble.py`, `render_prod.py --check`)가 한 번에 바뀌고, 혹시 남은 소비자도 깨지지 않습니다 |
| 감성 100% | 범위 안(`in_window: true`)으로 봅니다 | 기존 원칙("웃기지 않은 장면에 예능 자막을 붙이는 것이 비율 미달보다 나쁘다") 유지 |
| 새 kind | `narration`(group `mood`). 최대 4줄, 줄당 22자. 줄 단위로 차례로 나타남 | 대사 없는 장면에서 자막만으로 이야기를 전하는 용도. 기존 `mood`(최대 2줄, 한 문장)와 역할이 다름 |
| 줄 수 제한 | kind 사양에 선택 필드 `max_lines`를 둡니다. 없으면 전역 `max_lines`(2) | 기존 kind 동작 불변 |
| 기본 preset 순서 | kind의 첫 preset이 기본입니다. 감성 친화 preset을 맨 앞에 둡니다: `variety`→`deadpan`, `situation`→`box-dark`, `sfx_text`→`pen-sfx`, `inner_voice`→`pen-note`, `dialogue`→`dialogue-soft`, `mood`→`soft-caption`, `narration`→`diary` | timeline v2는 preset을 반드시 적으므로 기존 timeline에는 영향이 없습니다. preset을 생략한 후보 카드만 새 기본값을 씁니다 |
| 기존 preset | 33개 모두 유지, 모양도 바꾸지 않습니다 | 기존 run을 다시 렌더해도 같은 모양. 예능 preset은 문서에서 "거의 안 씀"으로 내립니다 |
| 화면 톤(look) | timeline 최상위 선택 필드 `look`. 없으면 지금과 똑같이 렌더 | 하위 호환. 감성 기본값은 문서와 `presets.json`의 `look.recommended`로 제안만 합니다 |
| 효과 | `effects`에 `light_leak` 추가. 클립에 `transition: "dissolve"`와 `drift: true`(영상 느린 줌) 추가 | 기존 `punch_zoom`·`shake`·`flash`·`speedlines`·`fade`·`whip` 유지 |
| Skill 이름 | `k-variety-caption`을 **`k-mood-caption`으로 바꿉니다** | Skill은 description으로 호출이 정해집니다. "예능 80" 이름·설명이 남으면 감성 자막 작업에서 잘못 고르거나 놓칩니다. 이력 문서(`reports/`, 과거 spec, `feature_list.json`)의 옛 이름은 기록이므로 그대로 둡니다 |
| 공유 상수 | 내레이션 읽기 시간, look 상한, 디졸브 길이, 드리프트 배율은 모두 `presets.json`에 둡니다. Python 검증기와 렌더러가 같은 파일을 읽습니다 | 기존 "presets.json 하나가 원본" 구조를 따름 |
| 새 폰트 | 넣지 않습니다 | 승인 폰트(Gowun Batang, Nanum Pen Script, Cormorant Garamond, Nanum Gothic ExtraBold 등)로 충분. 선택 항목은 14절 |

## 3. `presets.json` 목표 모양

`renderer/src/production/presets.json`을 아래처럼 바꿉니다(키 순서 유지, 기존 kind의 preset 목록은 순서만 바꾸고 새 preset을 추가).

```json
{
  "target_mood_share": 0.9,
  "share_window": [0.8, 1.0],
  "max_lines": 2,
  "max_sub_chars": 36,
  "max_same_preset_in_a_row": 2,
  "narration": {"read_base_seconds": 0.6, "read_per_char_seconds": 0.12, "min_seconds": 2.5, "fade_frames": 15},
  "soft_fade_frames": 18,
  "look": {
    "grades": ["none", "warm", "faded", "film"],
    "max_grade_strength": 1.0,
    "max_grain": 0.25,
    "max_vignette": 0.5,
    "letterbox": [2.0, 2.39],
    "recommended": {"grade": "warm", "grade_strength": 0.5, "grain": 0.08, "vignette": 0.2, "letterbox": null}
  },
  "motion": {"dissolve_frames": 15, "drift_scale": 1.05, "light_leak_min_frames": 15},
  "kinds": {
    "variety": {"group": "variety", "max_chars": 18, "presets": ["deadpan", "pop", "shout", "punch", "drop", "shake"]},
    "situation": {"group": "variety", "max_chars": 28,
                  "presets": ["box-dark", "box-yellow", "box-pink", "box-mint", "box-sky", "ribbon", "sticker", "stamp", "bubble"]},
    "sfx_text": {"group": "variety", "max_chars": 8, "presets": ["pen-sfx", "tilt-red", "tilt-blue", "burst", "whoosh"]},
    "inner_voice": {"group": "variety", "max_chars": 24, "presets": ["pen-note", "bracket", "whisper", "thought"]},
    "dialogue": {"group": "dialogue", "max_chars": 32, "presets": ["dialogue-soft", "dialogue", "dialogue-box"]},
    "mood": {"group": "mood", "max_chars": 26,
             "presets": ["soft-caption", "blur-in", "bilingual", "serif-fade", "serif-low", "editorial", "letter-fade", "film-line", "pen-script"]},
    "narration": {"group": "mood", "max_chars": 22, "max_lines": 4, "presets": ["diary", "diary-center", "letter", "typewriter"]},
    "place": {"group": "mood", "max_chars": 20, "presets": ["place-card", "place-editorial", "chapter"]}
  }
}
```

새 preset은 10개입니다: `deadpan`(variety), `dialogue-soft`(dialogue), `soft-caption`·`blur-in`·`bilingual`(mood), `diary`·`diary-center`·`letter`·`typewriter`(narration), `chapter`(place). 합계 **43개**(기존 33 + 10)입니다.

## 4. 렌더러 사양

모든 크기는 1920×1080 기준입니다. 색은 크림 화이트 `#fbf6ec`를 기본으로 합니다. "얇은 그림자"는 `THIN = '0 1px 2px rgba(0,0,0,0.55), 0 0 12px rgba(0,0,0,0.25)'`입니다(Captions.tsx 상수).

### 4.1 공유 헬퍼 `renderer/src/production/mood.mjs` (새 파일)

`renderer/src/gain.mjs`처럼 JSDoc 타입을 단 순수 함수만 둡니다(`allowJs`·`checkJs` 켜져 있음). React·Remotion을 import하지 않아 `node --test`로 바로 시험할 수 있습니다.

- `softFade(frame, duration, frames)`: `f = Math.max(1, Math.min(frames, Math.floor((duration - 1) / 2)))`로 줄인 뒤 `[0, f, duration - f, duration] → [0, 1, 1, 0]`을 선형 보간하고 0..1로 자릅니다. 짧은 cue에서도 입력 구간이 항상 증가합니다.
- `narrationLineStarts(lines, duration, fps, rules)`: `rules`는 `presets.json`의 `narration` 블록. 줄마다 `read = round(fps * (read_base_seconds + read_per_char_seconds * 공백 뺀 글자 수))`. `starts[0] = 0`, `starts[i] = starts[i-1] + read[i-1]`. `limit = max(0, duration - fade_frames - fps)`(마지막 줄이 사라지기 전 최소 1초 온전히 보이게). `starts[last] > limit`이면 모든 값에 `limit / starts[last]`를 곱해 반올림. 정수 배열을 돌려줍니다.
- `narrationSeconds(text, rules)`: `max(min_seconds, Σ 줄별 (read_base_seconds + read_per_char_seconds * 공백 뺀 글자 수) + fade_frames/30 + 1)`. Python과 같은 식(5.2절)이며 권장 노출 시간입니다.
- `gradeFilter(grade, strength)`: `{filter, tint}`를 돌려줍니다. `s = strength`.
  - `none`: `{filter: 'none', tint: null}`
  - `warm`: `filter = sepia(0.18s) saturate(1+0.08s) hue-rotate(-4s deg) brightness(1+0.02s)`, `tint = {color: rgba(255,180,110,0.07s), blend: 'soft-light'}`
  - `faded`: `filter = contrast(1-0.12s) saturate(1-0.18s) brightness(1+0.03s)`, `tint = {color: rgba(60,50,40,0.10s), blend: 'lighten'}`(검정을 살짝 띄움)
  - `film`: `filter = sepia(0.12s) contrast(1-0.08s) saturate(1-0.1s)`, `tint = {color: rgba(255,190,130,0.06s), blend: 'soft-light'}`
  - 숫자는 소수 셋째 자리로 반올림해 문자열에 넣습니다.
- `letterboxBar(aspect, width = 1920, height = 1080)`: `Math.max(0, Math.round((height - width / aspect) / 2))`. 2.39 → 138, 2.0 → 60.
- `lightLeakOpacity(frame, duration, strength)`: 피크 `Math.min(0.5, 0.3 * strength)`. `[0, 0.3d, 0.6d, d] → [0, peak, peak, 0]`(d가 작아도 증가하도록 `softFade`처럼 보정).

### 4.2 `Captions.tsx`

- `Motion`에 `soft: number`(=`softFade(frame, duration, registry.soft_fade_frames)`)를 추가합니다. 기존 `pop`·`fade`는 그대로입니다. `presets.json`은 `import registry from './presets.json'`로 읽습니다(CaptionGallery와 같은 방식).
- 첫 줄 주석을 "Mood (감성) presets lead (~90% of styled captions); variety presets stay for a light touch."로 바꿉니다.
- 새 `STYLES` 항목(테스트가 키를 정규식으로 읽으므로 기존처럼 2칸 들여쓰기, `'이름': (` 형식):
  - `deadpan`: Nanum Gothic ExtraBold(`FONTS.dialogue`) 34px, `#f2f2f2`, `textShadow: THIN`, opacity `fade`, 움직임 없음. 툭 던지는 작은 받아치기. 권장 위치 `lower_right`.
  - `dialogue-soft`: Gowun Batang 44px, `speakerColor(cue.speaker, '#fbf6ec')`, `textShadow: THIN`, 외곽선 없음, opacity `soft`.
  - `soft-caption`: Gowun Batang 38px, `#fbf6ec`, letterSpacing 1, lineHeight 1.6, `textShadow: THIN`, opacity `soft`, `translateY((1 - soft) * 6px)`.
- 새 `LAYOUTS` 항목:
  - `blur-in`: Gowun Batang 54px, 가운데 정렬. 첫 24프레임 동안 opacity 0→1, blur 10px→0, letterSpacing 4→2. 마지막 15프레임 동안 opacity 1→0, blur 0→6px. `sub`가 있으면 아래에 Cormorant 이탤릭 28px(opacity 0.85, 10프레임 늦게).
  - `bilingual`: 한 줄 Gowun Batang 40px + 아래 `sub`를 Cormorant 이탤릭 30px, letterSpacing 2, opacity 0.85. 한글은 `soft`, 영문은 8프레임 늦게 `soft`. `sub`가 없으면 한글만.
  - `diary`: 내레이션. `cue.text.split('\n')`의 줄을 `narrationLineStarts`로 차례로 보여줍니다. 줄마다 `t = clamp((frame - start) / fade_frames)`, opacity `t * out`, blur `(1 - t) * 4px`, `translateY((1 - t) * 8px)`. `out`은 마지막 `fade_frames` 동안 1→0(모든 줄 함께). Gowun Batang 40px, 왼쪽 정렬, lineHeight 1.7, letterSpacing 1, `textShadow: THIN`. `sub`가 있으면 마지막 줄 뒤 시작 시각에 Cormorant 이탤릭 28px 한 줄로 나타납니다. 권장 위치 `lower_left`.
  - `diary-center`: `diary`와 같되 가운데 정렬, 44px. 권장 위치 `center`.
  - `letter`: `diary`와 같은 줄 순서, Nanum Pen Script 66px, `#fff8e8`, lineHeight 1.35, 왼쪽 정렬, blur 없이 `translateY` 6px만. 편지·손글씨 메모 느낌.
  - `typewriter`: 줄 시작은 `narrationLineStarts`, 줄 안에서 글자를 `read * 0.6` 동안 차례로(글자당 4프레임 opacity 0→1, blur 없음). Gowun Batang 38px, 왼쪽 정렬.
  - `chapter`(place): Cormorant 96px, weight 300, 대문자, letterSpacing `18 - 6 * soft`(`cue.sub ?? cue.text`), 아래 1px 선(폭 0→160px, 프레임 6–24), 그 아래 Gowun Batang 32px 한글(`cue.text`). 전체 opacity `soft`, 가운데 정렬. 예: `sub: "DAY 1"`, `text: "첫째 날, 제주"`. 권장 위치 `center`.
- 내레이션 layout 세 개(`diary`, `diary-center`, `letter`)는 내부 함수 하나(`narrationLayout(options)`)로 만들고, `LAYOUTS`에는 `diary: narrationLayout({...}),` 형식으로 등록합니다. 테스트 정규식 `^  '?([a-z][a-z-]*)'?: [a-zA-Z(]`에 맞는지 확인합니다.
- `PRESET_NAMES`는 그대로 `STYLES`·`LAYOUTS` 키에서 나옵니다.

### 4.3 `Look.tsx` (새 파일)

- `export type LookSpec = {grade?: 'none'|'warm'|'faded'|'film'; grade_strength?: number; grain?: number; vignette?: number; letterbox?: number | null}`
- `export const lookFilter = (look?: LookSpec) => look ? gradeFilter(look.grade ?? 'none', look.grade_strength ?? 0.6).filter : 'none'`
- `export const LookOverlay = ({look}: {look?: LookSpec})`: `look`이 없으면 `null`. 위에서 아래 순서로 그립니다.
  1. tint: `AbsoluteFill`에 `background: tint.color`, `mixBlendMode: tint.blend`
  2. vignette(>0): `radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,${vignette}) 100%)`
  3. grain(>0): 960×540 인라인 SVG(`feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed={frame % 12}` + `feColorMatrix` 흑백)를 2배로 키워 덮고 `mixBlendMode: 'overlay'`, `opacity: grain`. `useCurrentFrame()`으로 seed를 바꿔 결정적으로 움직입니다(Math.random 금지).
  4. letterbox(값 있음): 위아래 검정 막대, 높이 `letterboxBar(letterbox)`.
- 자막은 LookOverlay **위**에 그립니다(자막은 색보정·그레인을 받지 않고, 레터박스 막대 위에 올라갈 수 있음).

### 4.4 `Effects.tsx`

- `EffectCue.type`에 `'light_leak'` 추가.
- `EffectOverlay`: `light_leak`이면 따뜻한 radial-gradient 두 개(`rgba(255,170,90,0.9)`, `rgba(255,120,160,0.6)`)를 화면 왼쪽 밖에서 오른쪽으로 프레임에 따라 천천히 이동(전체 길이 동안 -30% → 110%), `mixBlendMode: 'screen'`, opacity `lightLeakOpacity(frame, duration, strength)`.
- `effectTransform`은 바꾸지 않습니다(light_leak은 화면을 움직이지 않음).
- 파일 첫 주석을 "Short camera effects: variety (punch_zoom, shake, flash, speedlines) and mood (light_leak)."로 바꿉니다.

### 4.5 `ProductionTimeline.tsx`

- `Clip` 타입에 `drift?: boolean` 추가. timeline 타입에 `look?: LookSpec` 추가.
- 디졸브: 클립 i+1의 `transition`이 `'dissolve'`이면 클립 i의 `Sequence` `durationInFrames`를 `duration + D`(D=`registry.motion.dissolve_frames`)로 늘립니다. 클립 i+1은 `interpolate(frame, [0, D], [0, 1])` opacity로 위에 겹칩니다(DOM 순서상 뒤 클립이 위). 원본음 cue는 늘리지 않습니다(소리는 컷 그대로).
- 드리프트: 영상 클립에 `drift: true`면 scale을 `zoom → min(3, zoom * drift_scale)`로 클립 길이 동안 선형 보간합니다. 사진 클립은 지금처럼 1→zoom.
- 레이어 순서: 그림 레이어(`transform: effectTransform`, `filter: lookFilter(look)`) → EffectOverlay → 오디오 → 사진 overlay(같은 `filter` 적용한 `AbsoluteFill`로 감쌈) → `<LookOverlay look={timeline.look} />` → 자막.
- `look`이 없고 새 필드가 없으면 출력이 지금과 같아야 합니다.

### 4.6 `CandidatePreview.tsx`

- props에 `look?: LookSpec` 추가, `Segment`에 `drift?: boolean` 추가. 영상 segment의 `drift`는 4.5절과 같은 식으로 scale을 보간합니다.
- 레이어 순서는 4.5절과 같습니다. 후보 카드의 기대 화면에 색감·레터박스·그레인이 보이게 하기 위함입니다.
- 디졸브는 후보 미리보기에 그리지 않습니다(조립 뒤에만 의미가 있음). 카드 문구로만 표시(5.4절).

### 4.7 `CaptionGallery.tsx`와 `LookGallery`

- 모든 셀의 `Sequence`를 `from={-60} durationInFrames={180}`, cue `duration: 180`으로 바꿉니다. still은 30프레임에서 찍으므로 셀은 로컬 90프레임, 즉 차례로 나타나는 내레이션까지 모두 보인 상태가 됩니다.
- `SAMPLES`/`SUBS`/`POSITION`에 추가:
  - `narration`: `'오늘은 조금 천천히 걷기로 했다\n바람이 먼저 와 있었다\n그걸로 충분했다'`, sub `'a slow day'`, 위치 `lower_left`
  - `mood` 샘플은 유지, `place` sub는 `'PHU QUOC'` 유지(`chapter`는 `sub`를 크게 씀)
  - `dialogue`, `variety` 등 기존 샘플 유지
- 셀 라벨의 `group · kind · preset`은 그대로.
- 첫 줄 주석을 "One cell per preset so the mood-first caption system can be reviewed at a glance."로 바꿉니다.
- 새 composition `LookGallery`(같은 파일 또는 `LookGallery.tsx`): 960×540 셀 2열. 배경은 합성 풍경(하늘→바다 `linear-gradient`와 원형 해 하나, 미디어 파일 없음) 위에 `bilingual` 자막 한 줄. 셀: `none`, `warm`, `faded`, `film`, `recommended`(presets.json의 `look.recommended`), `letterbox 2.39`, `vignette 0.4 + grain 0.2`, `light_leak`(strength 1, still 프레임이 피크에 오도록 Sequence offset 조정). 라벨은 셀 오른쪽 아래.
- `renderer/src/Timeline.tsx`의 `Root`에 `LookGallery` composition을 등록합니다.
- `renderer/scripts/gallery.mjs`: 두 번째 인자로 composition id를 받습니다(`CaptionGallery` 기본, `LookGallery` 허용, 그 밖은 오류). 출력 경로 제한은 그대로.

## 5. Python 사양

### 5.1 `scripts/production.py`

- 상수: `TRANSITIONS = {"cut", "fade", "whip", "dissolve"}`, `EFFECT_TYPES`에 `"light_leak"` 추가. `MOTION = CAPTION_REGISTRY["motion"]`, `LOOK = CAPTION_REGISTRY["look"]`, `NARRATION = CAPTION_REGISTRY["narration"]`.
- `validate_caption_text`: 줄 수 한도를 `spec.get("max_lines", CAPTION_REGISTRY["max_lines"])`로 읽고, 오류 문구도 그 값을 씁니다.
- `narration_seconds(text)`: 4.1절 `narrationSeconds`와 같은 식.
- `validate_look(look)`: dict가 아니면 오류. 허용 키는 `grade`, `grade_strength`, `grain`, `vignette`, `letterbox`뿐(그 밖 키는 오류). `grade ∈ LOOK["grades"]`; `grade_strength`·`grain`·`vignette`는 bool이 아닌 유한 숫자이며 각각 `0..max_grade_strength`, `0..max_grain`, `0..max_vignette`; `letterbox`는 `None` 또는 `LOOK["letterbox"]`의 값. 통과하면 dict를 돌려줍니다.
- `validate_timeline_v2`:
  - `"look" in timeline`이면 `validate_look`.
  - 클립: `drift`는 bool이고 영상 클립에만 허용(사진 클립에 `drift`가 있으면 오류 "Photos already drift"). `transition == "dissolve"`면 첫 클립이 아니고, 이 클립과 바로 앞 클립의 `duration`이 `D` 이상이고, 앞 클립이 영상이면 `prev.in + ceil((prev.duration + D) * prev.speed) <= frames`(아니면 "Dissolve needs D more source frames after the previous clip").
  - 자막: `kind == "narration"`이고 `duration < round(NARRATION["min_seconds"] * 30)`이면 오류.
  - 효과: `light_leak`이고 `duration < MOTION["light_leak_min_frames"]`면 오류. strength 범위(0.5..2)는 기존 그대로.
- `narration_warnings(captions, fps=30)`: `narration` 자막의 노출 시간(timeline은 `duration / fps`, 후보는 `duration` 초)이 `narration_seconds(text)`보다 짧으면 `"'<앞 12자>…' 내레이션이 읽기에 짧습니다(현재 X초, 권장 Y초)"`를 돌려줍니다. 경고일 뿐 거부하지 않습니다.
- `caption_style_share` 재작성:

```python
def caption_style_share(timeline):
    """Report the mood/variety caption split. A guide for review, never an enforced quota."""
    counts = {"mood": 0, "variety": 0, "dialogue": 0}
    for caption in timeline.get("captions", []):
        kind = caption.get("kind")
        counts["mood" if kind in MOOD_CAPTIONS else "variety" if kind in VARIETY_CAPTIONS else "dialogue"] += 1
    styled = counts["mood"] + counts["variety"]
    mood = round(counts["mood"] / styled, 2) if styled else None
    low, high = CAPTION_REGISTRY["share_window"]
    return {**counts, "mood_share": mood, "variety_share": None if mood is None else round(1 - mood, 2),
            "target": CAPTION_REGISTRY["target_mood_share"], "in_window": mood is not None and low <= mood <= high}
```

### 5.2 `scripts/review.py`

- `KIND_LABELS`에 `"narration": "내레이션"` 추가.
- `validate_candidates`:
  - `plan.transition`이 있으면 `production.TRANSITIONS` 안이어야 합니다(지금은 검사하지 않음).
  - `plan.drift`는 bool이고 영상 후보에만.
  - 자막 `kind == "narration"`이면 `duration >= NARRATION["min_seconds"]`.
  - effect `light_leak`이면 `duration >= MOTION["light_leak_min_frames"] / 30`.
- 새 함수 `candidates_look(data)`: `data.get("look")`이 없으면 `None`, 있으면 `production.validate_look`. `build`에서 호출해 각 후보의 `render_props(..., look=look)`에 넘깁니다.
- `render_props`: `look=None` 인자 추가, 결과에 `"look": look` 포함(없으면 키 생략). 영상 segment에 `"drift": plan.get("drift", False)`.
- `card_html`: 편집 계획 목록에 `디졸브(조립 후 확인)` / `느린 줌` 표시. look이 있으면 페이지 머리에 `화면 톤: warm 0.5 · grain 0.08 · vignette 0.2` 한 줄.
- `page_html` 비율 문구:

```python
ratio = ("자막 비율: 스타일 자막 없음" if share["mood_share"] is None else
         f"자막 비율: 감성 {share['mood']} · 예능 {share['variety']} · 대사 {share['dialogue']} "
         f"(감성 {share['mood_share']:.0%}, 목표 {share['target']:.0%} 참고" +
         ("" if share["in_window"] else " · 목표 범위 밖") + ")")
```

  `preset_warnings` 뒤에 `production.narration_warnings(...)`(후보 기준, 초 단위)도 붙입니다.

### 5.3 `scripts/assemble.py`

- 후보 파일 데이터의 `look`(`review.candidates_look`)을 `timeline["look"]`으로 옮깁니다(없으면 키 없음).
- 영상 클립에 `plan.get("drift")`가 참이면 `clip["drift"] = True`.
- 디졸브 보정: 첫 클립의 `dissolve`는 `fade`로 바꾸고 경고 `"<cid>: 영상 첫 장면은 디졸브할 앞 장면이 없어 페이드로 바꿨습니다"`. 앞 클립 길이·원본 여유가 부족하면 `cut`으로 바꾸고 경고 `"<cid>: 앞 장면 원본 여유가 부족해 디졸브 대신 컷"`. 보정은 `validate_timeline_v2` 호출 전에 합니다.
- `narration_warnings(captions)`를 `warnings`에 더합니다.
- 보고서 줄: `f"- 자막: 감성 {share['mood']} · 예능 {share['variety']} · 대사 {share['dialogue']}" + (f" (감성 {share['mood_share']:.0%})" if share["mood_share"] is not None else "")`. look이 있으면 `- 화면 톤: ...` 한 줄.

### 5.4 `scripts/render_prod.py`

- 코드 변경 없음(`caption_style_share` 결과 모양만 바뀜). `--check` 출력에 `mood_share`가 들어가는지 테스트로 확인합니다.

## 6. 테스트

기대값 변경은 아래에 적은 것만 합니다.

### 6.1 바꾸는 기대값 (계약 변경으로 허용)

- `tests/test_captions.py`
  - `test_groups_cover_variety_mood_and_dialogue`: `assertEqual(REGISTRY["target_mood_share"], 0.9)`, `assertNotIn("target_variety_share", REGISTRY)`.
  - `test_share_is_reported_against_the_window`: `["mood"]*9 + ["variety"]` → in_window True; `["mood"]*5 + ["variety"]*5` → False; `["mood"]*10` → True(감성 100% 허용); `["variety"]*10` → False; `["narration"]*2 + ["place"]` → `mood_share == 1.0`; `["dialogue"]` → `mood_share is None`.
  - `test_review_page_shows_caption_ratio`: 문구를 `"자막 비율: 감성 1 · 예능 3 · 대사 0 (감성 25%, 목표 90% 참고 · 목표 범위 밖)"`로.
  - 모듈 docstring의 "80/20"을 "mood-first ratio"로.
- `tests/test_production.py::test_caption_share_is_reported_not_enforced`: `(share["mood"], share["variety"], share["mood_share"]) == (1, 4, 0.2)`; 감성만 3개면 `mood_share == 1.0`이고 `in_window`가 True.
- `tests/test_skills.py`: `CUSTOM`의 `"k-variety-caption"` → `"k-mood-caption"`, `test_caption_skill_limits_match_registry`가 `frontmatter("k-mood-caption")`을 읽음.

### 6.2 추가하는 테스트

- `tests/test_captions.py`
  - `test_narration_allows_four_lines_of_22`: 4줄 통과, 5줄 거부, 23자 줄 거부, `mood`는 여전히 3줄 거부.
  - `test_mood_friendly_defaults`: `require_preset=False`일 때 기본 preset이 3절 표와 같음(`variety→deadpan`, `mood→soft-caption`, `narration→diary`, `dialogue→dialogue-soft`).
  - `test_old_presets_still_registered`: 2026-10-22 이전 33개 preset 이름 목록을 테스트에 적고 모두 registry에 있는지 확인.
  - `test_narration_reading_time`: `narration_seconds("가나다라마바사아자차")` 값 확인(0.6+1.2+0.5+1 = 3.3), 짧은 cue에 `narration_warnings`가 경고 1개, 충분한 cue는 0개.
- `tests/test_production.py`
  - `test_look_is_optional_and_bounded`: look 없음 통과; `{"grade": "warm", "grade_strength": 0.5, "grain": 0.08, "vignette": 0.2, "letterbox": 2.39}` 통과; `grade: "teal"`, `grain: 0.3`, `vignette: True`, `letterbox: 1.85`, 모르는 키 `"lut"`, `grade_strength: 1.2` 각각 거부.
  - `test_dissolve_and_drift_rules`: fixture에서 `c2`에 `dissolve`(앞 클립 v1 in 30, speed 1.5, 120프레임 → 30 + ceil(135 × 1.5) = 233 ≤ 300) 통과; 첫 클립 dissolve 거부; 앞 클립 원본 여유 부족(`v1.frames = 210`) 거부; 사진 클립 `drift` 거부; `drift: "yes"` 거부.
  - `test_narration_and_light_leak_minimums`: narration 74프레임 거부·75 통과, light_leak 14프레임 거부·15 통과.
  - `test_existing_fixture_still_valid`: 변경 없는 `edit_fixture()`가 240을 돌려줌(하위 호환 고정).
- `tests/test_review.py`(기존 fixture 함수 재사용)
  - 후보 데이터에 `look`을 넣으면 `render_props(..., look=...)` 결과에 들어감; 잘못된 look은 `ValueError`.
  - `plan.transition: "spin"` 거부, 사진 후보의 `drift` 거부.
- `tests/test_skills.py`
  - `test_caption_skill_limits_match_registry`에 `f"내레이션 {registry['narration']['max_chars']}자"`와 `f"{registry['narration']['max_lines']}줄"`이 Skill 본문에 있는지 추가.
  - `test_no_stale_ratio_strings`: `CLAUDE.md`, `README.md`, `docs/caption-style.md`, `docs/workflow.md`, 네 개 custom Skill, `config/production.example.json`에 `"예능 80"`, `"variety 80"`, `"fun 60"`, `"재미 60"`, `"k-variety-caption"`이 없음.
- `tests/test_phase_configs.py` 또는 `tests/test_production.py`: `config/production.example.json`의 `caption_style == "mood 90 / variety 10"`.
- `renderer/tests/mood.test.mjs`(새 파일, `node --test`가 자동으로 잡음)
  - `softFade`: duration 3·10·200에서 예외 없이 0..1, 중간값 1.
  - `narrationLineStarts`: 한 줄 → `[0]`; 세 줄 → 증가, 마지막 값 ≤ `duration - fade_frames - fps`; 짧은 duration에서도 음수 없음. rules는 `presets.json`을 `fs`로 읽어 넘깁니다.
  - `gradeFilter`: `none` → `'none'`과 `tint: null`; strength 0인 `warm`은 `sepia(0)`을 포함; 네 grade가 모두 문자열 반환.
  - `letterboxBar(2.39) === 138`, `letterboxBar(2.0) === 60`.
  - `lightLeakOpacity` 피크 ≤ 0.5(strength 2에서도).

## 7. 문서·Skill

### 7.1 `docs/caption-style.md` 전면 재작성

제목 `# 자막 스타일 가이드 (감성 90 · 예능 10)`. 절 구성:

1. 머리말: 목표는 **풍경과 일상의 결을 보여주는 감성 브이로그**. 예능은 강조할 순간에만 살짝. 원본은 `presets.json`, 모양은 `reports/caption-gallery.jpg`·`reports/look-gallery.jpg`(병합 뒤 생성, 명령 `node renderer/scripts/gallery.mjs reports/caption-gallery.jpg`와 `... reports/look-gallery.jpg LookGallery`).
2. **90 · 10의 의미**: 감성 계열(`mood`·`narration`·`place`) 약 90%, 예능 계열 약 10%, `dialogue` 제외. 80–100%는 범위 안. 감성 100%도 괜찮음. 웃긴 순간이 실제로 있을 때만 예능 자막.
3. **레퍼런스 관찰 요약**: 1절 표를 3–5줄로 요약하고 이 plan 문서를 링크. "확인/추정" 구분 유지.
4. **kind와 preset** 표: 3절의 순서대로, 새 preset 설명 포함. 예능 계열 행에 "감성 브이로그에서 쓰는 것: `deadpan`, `pen-note`, `whisper`, `pen-sfx`, `box-dark`. 나머지(`pop`, `shout`, `burst`, `box-yellow` 등)는 유지하지만 거의 쓰지 않음" 명시. `narration` 행: 4줄 × 22자.
5. **내레이션 작법**: 1인칭 일기·편지체, 현재 장면에서 출발해 감정은 한 줄만, 마지막 줄은 짧게 닫음. 한 장면 한 내레이션. 줄은 `\n`으로 나누며 줄이 차례로 나타남. 대사가 있는 구간에는 쓰지 않음. 예문 5개 이상:
   - `오늘은 조금 천천히 걷기로 했다\n바람이 먼저 와 있었다\n그걸로 충분했다` (sub `a slow day`)
   - `창문을 열자\n어제와 다른 냄새가 났다`
   - `계획은 없었다\n그래서 더 오래 머물렀다`
   - `엄마에게 보내고 싶은 풍경\n사진으로는 다 안 담겼다`(`letter`)
   - `돌아가는 길\n오늘을 조금 더 붙잡고 싶었다`
   - 나쁜 예: 형용사 나열(`너무너무 아름답고 행복하고 소중한 하루`), 시청자에게 말 걸기(`여러분 여기 꼭 가세요!!`), 사실이 아닌 사건.
   - **사실 경계**: 내레이션은 편집자가 쓴 독백임이 분명하므로 `dialogue`가 아닙니다. 촬영자의 실제 감정·행동을 단정하지 않고, 화면에서 보이는 것에서 출발합니다(기존 "하지 않는 것" 유지).
6. **타이밍**: 대사 자막 규칙(기존 절 유지). 감성 자막은 3–6초, 페이드 18프레임. 내레이션 권장 노출 = `max(2.5초, Σ줄(0.6초 + 0.12초 × 글자 수) + 1.5초)`, 최소 2.5초(미만은 거부), 권장보다 짧으면 경고. 내레이션이 있는 장면은 그 길이 이상이어야 하므로 후보의 컷을 내레이션에 맞춰 늘립니다(장면이 짧으면 문장을 줄임). 다음 장면으로 넘어가기 전에 끝냄.
7. **위치**: 내레이션 `lower_left`(기본)·`center`(풍경 가운데가 비었을 때)·`bottom`. 작은 감성 자막은 `bottom`. 얼굴·하늘선을 가리지 않음. 레터박스를 쓰면 `bottom` 자막은 아래 막대 위에 놓여도 됨.
8. **화면 톤과 효과**: `look`(timeline 최상위 / `candidates.json` 최상위) 필드 표와 상한, 권장값 `warm 0.5 · grain 0.08 · vignette 0.2 · letterbox 없음`. 레터박스 2.39는 오프닝·마무리처럼 "영화 같은" 묶음에만 권장(전역 적용이라 전체에 걸림). `light_leak`은 장면 전환·오프닝에 0.5–2초, 20초에 한 번 이하. `dissolve`(0.5초)는 시간·장소가 바뀌는 곳에만, 한 영상에 남발하지 않음. `drift`(영상 1.05배 느린 줌)는 정적인 풍경 컷에. 예능 효과(`punch_zoom`, `shake`, `flash`, `speedlines`)는 예능 10% 장면에서만.
9. **예능 10%**: 강조할 말 하나만 크기·색을 바꾸는 정도(강민경 관찰). 예: 정적인 장면 뒤 `deadpan` `(사실 길 잃음)`, `pen-note` `(배고픔 한계)`, `pen-sfx` `꼬르륵`. 한 화면 예능 자막 1개. 감성 장면·내레이션과 겹치지 않음.
10. **variation**, **하지 않는 것**, **확인 절차**: 기존 내용을 유지하되 비율 문구를 감성 기준으로.
11. 폰트 문단: 실제 번들 7종(Black Han Sans, Jua, Do Hyeon, Gowun Batang, Nanum Gothic ExtraBold, Nanum Pen Script, Cormorant Garamond)으로 고침(지금 문서는 5종만 적혀 있음).

기존 "첫 sample 피드백" 관련 내용(타이밍, 겹침 조정)은 그대로 살립니다.

### 7.2 `docs/editorial-guide.md`

"Brief와 길이" 문단의 "예쁜 구도와 예능 자막, 재미 60%·감성 40%"를 "감성 90 · 예능 10(2026-10-22 사용자 요청), 대사 없는 장면의 내레이션 자막"으로 바꾸고, "재미 장면이 흐름을 이끌게"를 "감성 장면이 흐름을 이끌고, 재미는 강조할 순간에만"으로 바꿉니다. "예능 코멘트는 `editorial`로 구분" 문장은 현재 kind 체계와 맞지 않으므로 "편집자 문장은 `narration`·`mood`·`inner_voice`로 구분"으로 고칩니다. 그 밖은 그대로 둡니다.

### 7.3 `docs/sound-guide.md`

첫 문단의 "예능 템포를 살리는 효과음"을 "현장음을 중심에 두고, BGM은 낮게, 효과음은 예능 장면에만"으로 바꿉니다. "감성 구간" 줄에 "내레이션 장면은 현장음 위에 BGM을 -20 dB 안팎으로 낮게 깔거나 BGM 없이 둠. 생활소음이 감성 브이로그의 핵심 요소(1절 오눅 관찰)"를 추가합니다. 숫자 상한·권리 절차는 바꾸지 않습니다.

### 7.4 `docs/workflow.md`, `docs/roadmap.md`, `README.md`, `CLAUDE.md`

- `CLAUDE.md` 33행: `(mood 90 / variety 10 with narration captions, presets from ...)`. 29행 Skill 이름 `k-mood-caption`.
- `README.md` 3행: "(감성 90 · 예능 10, 대사 없는 장면의 내레이션 자막)". 20행 Skill 이름.
- `docs/workflow.md` 9행 Skill 이름.
- `docs/roadmap.md`: 3행 목표 문장을 감성 90 · 예능 10으로; 5번 행은 기록이므로 그대로 두고 표 아래에 "2026-10-22 `mood-vlog-style`: 감성 90 · 예능 10 전환, narration kind, look·light_leak·dissolve·drift" 행 또는 줄을 추가; 42행 Skill 이름; 61행 "예능 80 · 감성 20의 체감"을 "감성 90 · 예능 10과 내레이션 자막의 체감"으로.
- `docs/superpowers/specs/2026-10-19-production-harness-design.md`: 본문은 승인된 기록이므로 고치지 않고, 제목 아래에 `> 2026-10-22: 자막 비율은 감성 90 · 예능 10으로 바뀌었습니다. [계획](../plans/2026-10-22-mood-vlog-style.md)` 한 줄만 추가합니다.
- `docs/superpowers/specs/2026-10-18-vlog-environment-design.md`, `reports/`, `feature_list.json`, `session-handoff.md`는 고치지 않습니다.

### 7.5 Skill

- `git mv .claude/skills/k-variety-caption .claude/skills/k-mood-caption`. `SKILL.md`를 다시 씁니다.
  - frontmatter `name: k-mood-caption`, `description: vlog-me 후보나 timeline에 감성 90 · 예능 10 스타일의 한국어 자막을 쓰거나 고칠 때 사용합니다. 풍경 장면의 내레이션(1인칭 독백, 여러 줄 차례로 등장)·감성·장소 자막과 가끔의 가벼운 예능 자막의 kind와 preset을 고르고, 화면 톤(look)과 감성 효과를 정하며, 사용자의 자막 수정 요청을 반영합니다.`
  - 본문: 쓰는 순서(① 장면이 감성인지 예능인지 판정 → ② 대사 없는 풍경이면 `narration` 또는 `mood` 하나, 장소 전환이면 `place`/`chapter` → ③ 내레이션 길이에 맞춰 컷 길이 조정 → ④ 웃긴 순간이 실제로 있을 때만 예능 자막 하나 → ⑤ look·효과 → ⑥ 리뷰 페이지의 감성 비율·내레이션 읽기 경고 확인).
  - 체크리스트에 정확한 문자열 `받아치기 18자`, `효과 글자 8자`, `내레이션 22자`, `4줄`을 넣습니다(테스트가 읽음).
  - 좋은 예/나쁜 예 표를 감성 중심으로 다시 씀(노을 해변 → `narration` 예문, 길 잃음 → `deadpan`, 감성 장면에 `shout` 금지).
  - "사용자가 자막 수정을 요청했을 때" 절은 그대로 옮기고 Skill 이름만 바꿈.
- `.claude/skills/vlog-scout/SKILL.md`: 목표 비율 문장을 "감성 90 · 재미 10. 감성 장면이 흐름을 이끌고, 재미는 실제로 웃긴 순간이 있을 때만 짧게"로. mood 기준을 "풍경·이동·빛·음식·조용한 순간, 생활소음이 좋은 구간. 내레이션을 얹을 장면은 4–10초로 넉넉하게"로 넓힘(기존 3–8초 문장 교체). 예시 JSON의 자막을 감성 예시로 교체하되 `test_scout_example_uses_registered_caption_kinds`가 통과해야 함. 예: mood 후보에 `{"kind": "narration", "text": "오늘은 조금 천천히 걷기로 했다\n바람이 먼저 와 있었다", "at": 0.5, "duration": 5.0, "position": "lower_left", "sub": "a slow day"}`. 연출 필드 목록에 `look`(파일 최상위), `transition: "dissolve"`, `drift: true`, effect `light_leak` 추가. `k-variety-caption` 참조 2곳 → `k-mood-caption`.
- `.claude/skills/vlog-workflow/SKILL.md`: 9행 "감성 90 · 예능 10의 YouTube 롱폼 브이로그", 12·32행 Skill 이름.
- `.claude/skills/vlog-sound/SKILL.md`: 43행 근처 "감성 구간은 현장음 위주" 뒤에 "내레이션 장면은 BGM을 낮게 깔거나 비움" 한 줄. 그 밖은 그대로.
- `config/skills-lock.json`: `k-variety-caption` 항목의 `name`·`path`를 `k-mood-caption`으로, `version`을 `"2"`로. 바뀐 네 Skill(`k-mood-caption`, `vlog-scout`, `vlog-workflow`, `vlog-sound`)의 `SKILL.md` hash를 `shasum -a 256`으로 다시 계산해 넣습니다. `remotion-best-practices`는 건드리지 않습니다.

## 8. 설정

- `config/production.example.json`: `"editorial_direction": "mood 90 / fun 10, quiet scenery and first-person narration with a light touch of everyday humor"`, `"caption_style": "mood 90 / variety 10"`. 다른 키는 바꾸지 않습니다.
- `config/setup.example.json`: 두 값이 `null`이므로 바꾸지 않습니다.
- `config/project.json`(live): **coding worker는 고치지 않습니다.** 12절 coordinator 작업입니다.

## 9. Task 순서

각 task 끝에 `./scripts/dev-check.sh`를 실행하고 PASS를 확인한 뒤 로컬 커밋합니다. FAIL이면 다음 task로 가지 않습니다.

| # | 내용 | 파일 | 검증 |
| --- | --- | --- | --- |
| T1 | 비율 계약 전환: `presets.json`의 `target_mood_share`·`share_window`, `caption_style_share`, review·assemble 문구 | `presets.json`(이 task에서는 비율 키만), `scripts/production.py`, `scripts/review.py`, `scripts/assemble.py`, `tests/test_captions.py`, `tests/test_production.py` | `python3 -m unittest tests.test_captions tests.test_production tests.test_review` + dev-check |
| T2 | `narration` kind와 kind별 `max_lines`, 읽기 시간 규칙·경고, 기본 preset 순서, 새 preset 10개 등록 + 렌더러 구현, `mood.mjs`의 `softFade`·`narrationLineStarts`·`narrationSeconds` | `presets.json`, `production.py`, `review.py`, `assemble.py`, `Captions.tsx`, `mood.mjs`, `renderer/tests/mood.test.mjs`, `tests/test_captions.py` | `test_renderer_implements_exactly_the_registered_presets` 통과, `npm --prefix renderer test`, dev-check |
| T3 | look: `validate_look`, `Look.tsx`, `gradeFilter`·`letterboxBar`, ProductionTimeline·CandidatePreview 레이어, candidates/assemble 전달 | `presets.json`(`look`), `production.py`, `review.py`, `assemble.py`, `Look.tsx`, `mood.mjs`, `ProductionTimeline.tsx`, `CandidatePreview.tsx`, 테스트 | `test_look_is_optional_and_bounded`, `test_existing_fixture_still_valid`, review look 테스트, dev-check |
| T4 | 효과·전환: `light_leak`, `dissolve`, `drift`(검증, 렌더러, assemble 보정, review 검증·카드 문구) | `presets.json`(`motion`), `production.py`, `review.py`, `assemble.py`, `Effects.tsx`, `ProductionTimeline.tsx`, `CandidatePreview.tsx`, `mood.mjs`, 테스트 | `test_dissolve_and_drift_rules`, `test_narration_and_light_leak_minimums`, dev-check |
| T5 | 갤러리: CaptionGallery 오프셋·내레이션 샘플, `LookGallery`, `gallery.mjs` 인자, `Timeline.tsx` 등록, env 게이트 미디어 테스트에 LookGallery 크기 검사 추가 | `CaptionGallery.tsx`, (`LookGallery.tsx`), `Timeline.tsx`, `gallery.mjs`, `tests/test_captions.py`(`GalleryMediaTests`) | dev-check(lint·typecheck). 갤러리 렌더는 실행하지 않음(`VLOG_MEDIA_TESTS` 미설정이라 skip) |
| T6 | 문서·설정: 7.1–7.4, 8절 | `docs/caption-style.md`, `docs/editorial-guide.md`, `docs/sound-guide.md`, `docs/workflow.md`, `docs/roadmap.md`, `README.md`, `CLAUDE.md`, 2026-10-19 spec 머리 한 줄, `config/production.example.json`, `tests/test_production.py`(example 값) | dev-check |
| T7 | Skill: 이름 변경, 네 Skill 갱신, skills-lock, `tests/test_skills.py`(이름, 내레이션 문자열, `test_no_stale_ratio_strings`) | `.claude/skills/*`, `config/skills-lock.json`, `tests/test_skills.py` | `python3 -m unittest tests.test_skills`, `python3 -c "import sys; sys.path.insert(0,'scripts'); import doctor; doctor.verify_skill_integrity(__import__('pathlib').Path('.').resolve())"`로 lock 검사, dev-check |
| T8 | 마무리 점검 | — | `git grep -n -E "예능 80|variety 80|fun 60|재미 60|target_variety_share|k-variety-caption"`의 남은 결과가 이력 문서(`reports/`, `feature_list.json`, `session-handoff.md`, 과거 spec 본문)뿐인지 확인. `git diff --stat main...HEAD`. 최종 dev-check |

T1과 T2가 같은 `presets.json`을 고치므로 한 worker가 순서대로 진행합니다(병렬 분할하지 않음).

## 10. 하위 호환 확인 목록

- 기존 timeline v2(새 필드 없음)는 그대로 통과합니다(`test_existing_fixture_still_valid`, 기존 `test_valid_edit_is_content_driven`).
- 기존 33개 preset은 이름·모양 그대로입니다(`test_old_presets_still_registered`).
- `look`이 없는 timeline은 그림 레이어 `filter: 'none'`, LookOverlay `null`로 지금과 같은 화면입니다.
- 바뀌는 것: (1) preset을 생략한 **후보 카드**의 기본 preset, (2) 리뷰 페이지·조립 보고서의 비율 문구, (3) `render_prod.py --check` 출력의 `captions` 모양(`mood_share` 추가). 기존 `work/prod-*`의 파일은 고치지 않습니다.

## 11. 범위 밖

- 실제 영상 편집, production·smoke 렌더, 기존 `work/prod-*` run의 timeline·후보·리뷰 수정.
- 갤러리 still 생성(`reports/` 쓰기는 coordinator 몫), Remotion Studio 실행.
- 폰트·음원·패키지 다운로드. 새 폰트 도입(14절 선택 항목).
- 후보 카드 미리보기의 디졸브 표현, `whip` 전환 렌더 구현(지금도 미구현, 그대로 둠).
- 오디오 크로스페이드(디졸브 구간의 소리는 컷 그대로).
- 클립·구간별 look(이번에는 timeline 전역 하나). 필요하면 다음 feature.
- `config/project.json`, `feature_list.json`, `progress.md`, `session-handoff.md`, `reports/` 수정.

## 12. 병합 뒤 coordinator 작업 (coding worker 아님)

1. main checkout에서 `config/project.json`의 `editorial_direction`과 `caption_style`을 8절 값으로 맞춥니다. 다른 키(phase, source_roots, audio_*, production_render 등)는 건드리지 않습니다. live config 값이 바뀌므로 사용자에게 알립니다.
2. `./init.sh` 실행.
3. 사용자 동의 뒤 갤러리 still 두 장 생성: `node renderer/scripts/gallery.mjs reports/caption-gallery-v2.jpg`, `node renderer/scripts/gallery.mjs reports/look-gallery.jpg LookGallery`(기존 `reports/caption-gallery.jpg`는 덮어쓰지 않음, `overwrite: false`). 문서 링크가 새 파일을 가리키는지 확인.
4. 사용자가 갤러리를 보고 크기·위치·톤 취향을 확인. 조정은 다음 작은 개발 task로.
5. `feature_list.json`, `progress.md`, `session-handoff.md`, `reports/README.md`의 현재 보고서 갱신.

## 13. 독립 리뷰 조건 해당 여부

`scripts/production.py`, `config/`, `renderer/src/production/`, `.claude/skills/`, `config/skills-lock.json`을 바꾸고 diff도 300줄을 넘을 것이므로 docs/orca.md의 독립 리뷰 조건 1·2·4·5에 해당합니다. 리뷰를 돌립니다.

## 14. 남은 질문과 선택 항목

1. **폰트·위치 취향 확인**: 두 채널의 자막 폰트와 위치는 출처로 확인하지 못했습니다. 갤러리를 본 뒤 사용자가 레퍼런스 영상 캡처(사용자가 직접 찍은 스크린샷)로 비교해 주면 크기·위치를 조정합니다.
2. **강민경 레퍼런스의 해석**: 확인된 출처상 강민경 채널은 예능식 편집입니다. 이 계획은 그 요소를 "예능 10"에만 반영했습니다. 사용자가 원한 것이 강민경의 다른 측면(레트로 카메라 색감 등)이라면 look의 `film` grade가 가장 가깝습니다.
3. **감성 100% 허용**: 범위 `[0.8, 1.0]`으로 감성만 있어도 "범위 안"입니다. 예능을 꼭 조금은 넣고 싶다면 상한을 0.95로 낮출 수 있습니다.
4. **선택 항목(기본 계획에 넣지 않음, 사용자 승인 후 다운로드)**: 더 얇은 명조(예: Noto Serif KR Light, 나눔명조 OFL)나 다른 손글씨 OFL 폰트. 승인되면 `config/fonts-lock.json`에 hash를 추가하는 별도 task로 진행합니다.
5. **레터박스 범위**: 지금 설계는 전역 하나입니다. 오프닝에만 레터박스를 원하면 구간별 look이 필요합니다(11절 범위 밖).
