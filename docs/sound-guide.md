# 사운드 가이드 (BGM · 효과음)

예능 템포를 살리는 효과음과 장면 묶음별 BGM을 고르고 등록·배치하는 기준입니다. 권리 판단의 원칙은 [설계 8절](superpowers/specs/2026-10-18-vlog-environment-design.md#세-플랫폼-공통-선별-기준)을 따르고, 이 문서는 실행 절차만 다룹니다. 실제 음원으로 청취해 확인한 취향 기준은 아직 없습니다.

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
  - 기본 음량은 -16 dB입니다.
  - 대사가 있는 구간은 전사 결과를 기준으로 자동으로 12 dB 낮춥니다(ducking). 페이드는 6프레임, 곡의 처음과 끝 페이드는 15프레임입니다.
  - `의심` 표시된 전사 구간은 ducking 기준에서 뺍니다.
- **효과음:** 리액션과 반전에만 씁니다.
  - 1분에 8개 이하를 권장합니다.
  - 같은 효과음을 3초 안에 반복하지 않습니다.
  - 넘으면 리뷰 카드에 `주의`로 표시하고, 거부하지는 않습니다.
  - 효과 글자 자막(`sfx_text`)과 같은 시점에 쓰면 효과가 커집니다.
- **감성 구간:** 현장음(파도, 바람, 거리 소리)을 살리고, 효과음은 넣지 않습니다.
- **원음 속 음악:** 촬영된 카페·매장 음악은 별도 BGM으로 해결되지 않습니다. 해당 구간을 보고하고 사용자와 처리 방법을 정합니다.
- 실제로 없던 소리를 현장음처럼 들리게 만들지 않습니다. 효과음은 편집적 강조로만 씁니다.

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
