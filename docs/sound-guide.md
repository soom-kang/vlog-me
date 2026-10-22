# 사운드 가이드 (BGM · 효과음)

현장음을 중심에 두고, BGM은 낮게, 효과음은 예능 장면에만 배치하는 기준입니다. 권리 판단의 원칙은 [설계 8절](superpowers/specs/2026-10-18-vlog-environment-design.md#세-플랫폼-공통-선별-기준)을 따르고, 이 문서는 실행 절차만 다룹니다. 실제 음원으로 청취해 확인한 취향 기준은 아직 없습니다.

## 음원 확보 경로

음원 파일은 `assets/audio/` 아래에 둡니다. 이 폴더는 Git에서 제외됩니다. 등록 기록은 `config/media-licenses.json`에 남깁니다.

1. **사용자가 직접 받은 파일 (`origin: user`)**
   - 예: YouTube 오디오 보관함에서 내려받은 곡을 `assets/audio/user/`에 넣습니다.
   - Claude가 출처와 이용 조건을 사용자에게 확인한 뒤 등록합니다.
2. **Claude가 찾은 무료 음원 (`origin: claude_search`)**
   - production config의 `audio_search`와 `audio_downloads`가 둘 다 `true`여야 합니다. 이 값은 사용자가 요청할 때만 바꿉니다.
   - Claude는 장면 분위기별 후보를 표로 먼저 보여줍니다. 표에는 제목, 제작자, 공급처 URL, 이용 조건 URL, Content ID 관련 근거, 파일 크기가 들어갑니다.
   - **다운로드는 사용자가 채팅으로 승인한 파일만** `assets/audio/library/`에 받습니다. 대량 다운로드와 비공식 API는 쓰지 않습니다.
   - 우선 검토할 공급처는 설계 문서에 정리했습니다(Mixkit, YouTube Audio Library). Pixabay는 Content ID 등록 곡이 있으므로 개별 근거를 확인한 곡만 씁니다. 효과음은 Freesound의 CC0 파일을 우선 검토합니다.

## 등록

```bash
python3 scripts/audio_library.py register --id sfx-boing --kind sfx --file assets/audio/user/boing.wav --title "Boing" --source "YouTube Audio Library" --license "YouTube Audio Library" --license-status verified --license-evidence "https://..." --claim-status documented_low_risk --claim-evidence "..." --platforms youtube --moods silly
```

- ID는 `bgm-이름` 또는 `sfx-이름` 형식입니다. 파일을 바꾸면 새 ID로 다시 등록합니다.
- 등록할 때 길이·sample rate·loudness·true peak를 측정하고 hash를 기록합니다.
- 분위기 태그: `bright`, `calm`, `tense`, `silly`, `deflated`, `warm`, `epic`, `travel`
- 상태 확인은 `python3 scripts/audio_library.py check --platforms youtube`로 합니다. 파일이 바뀌었으면 실패합니다.
- 설명란에 넣을 출처 표기는 `python3 scripts/audio_library.py credits --ids bgm-walk,sfx-boing`로 만듭니다. 실제로 쓴 음원만 넣습니다.

## 사용 가능 판정

brief의 `audio_platforms`(기본 `youtube`)에 대해 다음을 모두 만족해야 미리보기·렌더에 들어갑니다.
- 무료이고, 대상 플랫폼 이용 권한이 확인됨(`allowed_platforms`)
- `license_status: verified`이고 근거가 있음
- `claim_status: documented_low_risk`이고 근거가 있음. `unknown`은 보류합니다.
- 알려진 Content ID 등록이나 whitelist가 필요한 곡이 아님
- 출처 표기가 필요하면 표기 문구가 있음

이 판정은 선별 기록일 뿐 claim이 없다는 보증이 아닙니다. 업로드 후 실제 플랫폼 결과는 `platform_check`에 따로 남깁니다. 기본값은 `not_checked`입니다.

## 배치 규칙

- **BGM:** 장면 묶음(도입, 이동, 사건, 마무리)마다 한 곡을 씁니다. 컷마다 곡을 바꾸지 않습니다.
  - 조립하면 같은 곡을 쓰는 연속 후보가 한 구간으로 이어집니다. 곡 길이보다 긴 장은 끝부분이 무음이 되므로 곡을 나눕니다.
  - 같은 곡을 여러 장에서 쓰면 앞 장이 멈춘 지점부터 이어서 재생하도록 `bgm.offset`을 적습니다. `bgm.offset`(초)은 곡을 그 위치부터 재생합니다. 같은 곡을 두 장에서 쓸 때 도입부가 반복되지 않게 하거나, 리뷰 미리보기를 이어 붙인 샘플에서 곡이 처음으로 돌아가지 않게 합니다. 조립에서는 구간의 첫 후보 값만 씁니다.
  - 기본 음량은 -16 dB입니다. 하우스 스타일에서는 곡마다 `gain_db = -27 - (곡의 integrated LUFS)`로 맞춰 장마다 BGM 크기를 비슷하게 둡니다([하우스 스타일](house-style.md)).
  - 대사가 있는 구간은 전사 결과를 기준으로 자동으로 12 dB 낮춥니다(ducking). 하우스 스타일에서는 카메라를 보고 말하는 후보의 BGM을 통째로 빼므로(`"bgm": "말하는 동안 BGM 없음"`) ducking은 쿠키처럼 BGM을 일부러 깔아 둔 후보에만 남습니다. 원음을 끈 후보와 음소거한 문장 아래에서는 낮추지 않습니다(리뷰 미리보기와 조립 모두). 페이드는 6프레임, 곡의 처음과 끝 페이드는 15프레임입니다.
  - `의심` 표시된 전사 구간은 ducking 기준에서 뺍니다.
- **효과음:** 리액션과 반전에만 씁니다.
  - 1분에 8개 이하를 권장합니다.
  - 같은 효과음을 3초 안에 반복하지 않습니다.
  - 넘으면 리뷰 카드에 `주의`로 표시하고, 거부하지는 않습니다.
  - 효과 글자 자막(`sfx_text`)과 같은 시점에 쓰면 효과가 커집니다.
- **감성 구간:** 현장음(파도, 바람, 거리 소리)을 살리고, 효과음은 넣지 않습니다. 내레이션 장면은 허용된 현장음 위에 BGM을 -20 dB 안팎으로 낮게 깔거나 BGM 없이 둡니다. 생활소음은 감성 브이로그의 핵심 요소입니다([계획 1절의 오눅 관찰](superpowers/plans/2026-10-22-mood-vlog-style.md#1-레퍼런스-관찰)). 아래 출연자 외 목소리 통제 규칙은 그대로 적용합니다.
- **원음 속 음악:** 촬영된 카페·매장 음악은 별도 BGM으로 해결되지 않습니다. 해당 구간을 보고하고 사용자와 처리 방법을 정합니다.
- 실제로 없던 소리를 현장음처럼 들리게 만들지 않습니다. 효과음은 편집적 강조로만 씁니다.

## 출연자 외 목소리 통제 (2026-10-20 피드백)

동행·행인의 목소리가 원음에 섞이지 않게 후보마다 원음을 다음 중 하나로 둡니다.
- **대사가 없는 후보:** `original_gain_db: -80`로 원음을 끄고 BGM으로 채웁니다.
- **출연자 대사가 있는 후보:** `"original": "dialogue_only"`를 씁니다. 출연자가 실제로 말하는 동안(목소리 시작 0.15초 전부터 끝난 뒤 0.3초까지)만 원음이 들리고, 자막이 읽기 시간 때문에 더 남아 있는 동안이나 대사 사이는 모두 음소거됩니다.
- 대사 안에 섞인 짧은 저음(맞장구 등)은 `mute`에 직접 적습니다.
- **출연자 목소리를 살리는 기준(2026-10-22 피드백):** 출연자가 화면 중심에서 카메라를 보고 혼자 말할 때만 `dialogue_only`로 살립니다. 풍경이나 주변을 비추는 동안 들어간 말소리는 출연자 목소리여도 끄고(`original_gain_db: -80`), 그 내용은 BGM 위의 감성 자막(`talk-note`)으로 옮깁니다. BGM은 차분한 곡만 씁니다.
- **두 사람 대화가 겹치는 후보(2026-10-22 피드백):** 목소리를 살리지 않습니다. `original_gain_db: -80`으로 원음을 모두 끄고 BGM만 깔며, 대화 내용은 자막으로 요약합니다. 동행을 암시하지 않는 문구 규칙은 [자막 가이드](caption-style.md#레퍼런스형-구어체-2026-10-22-피드백)를 따릅니다.

리뷰는 `scripts/voices.py`로 원음의 음높이를 50ms마다 재서 남성 음역(175 Hz 이하) 목소리가 남은 후보를 카드와 페이지 머리에 `주의`로 표시합니다. 결과는 `work/<run>/voices/<id>.json`에 캐시됩니다.
- 출연자 목소리가 반 옥타브로 잘못 측정되는 경우는 걸러내지만, 낮은 여성 목소리·웃음·엔진 소리를 잘못 잡거나 소음 속 남성 목소리를 놓칠 수 있습니다.
- 경고가 없어도 사람이 듣고 확인해야 합니다. 수치 결과를 청취 확인으로 기록하지 않습니다.

## 후보 카드에서 쓰는 법

`candidates.json`의 `plan`에 다음처럼 적습니다.

```json
"sfx": [{"name": "띠용", "at": 4.5, "asset": "sfx-boing", "gain_db": -6}],
"bgm": {"asset": "bgm-walk", "gain_db": -16, "note": "가볍게 걷는 템포"}
```

- `asset`이 있는 효과음·BGM은 리뷰 미리보기에 실제 소리로 들어갑니다. 파일은 run의 `audio/`로 복사되고 hash를 다시 확인합니다.
- `asset`이 없으면 카드에 계획만 표시합니다.
- 사용할 수 없는 음원을 지정하면 렌더 전에 이유와 함께 멈춥니다. 예: `claim_pending`.

## BGM 고르기: 들어 보고 결정

2026-10-19 첫 sample 피드백(추천 곡 Serene View가 좋았음)에 따라, BGM은 비교해 듣고 고릅니다.
1. 장면 묶음마다 후보 2–4곡을 고릅니다. 저장된 음원과 추천 음원(승인 후 받은 무료 곡)을 가능하면 반반 섞습니다.
2. 후보 카드의 `plan.bgm_options`에 넣고 리뷰를 만듭니다. 같은 장면을 곡별로 렌더한 "음악 비교" 영상이 카드에 붙습니다.
3. 사용자가 고른 곡을 `plan.bgm`에 넣습니다. 이후 리뷰에서는 `bgm_options`를 빼도 됩니다.

## 확인

- 수치 검사: 합성 테스트에서 대사 구간의 BGM이 약 12 dB 낮아지는 것을 렌더 결과로 측정합니다(`./scripts/smoke-media.sh`).
- 사람 청취: 효과음 타이밍, 반복 피로, ducking의 자연스러움은 사용자가 미리보기로 듣고 판단합니다. 수치 통과를 청취 완료로 기록하지 않습니다.
