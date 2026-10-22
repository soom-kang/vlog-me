---
name: vlog-scout
description: 분석이 끝난 vlog-me run에서 재밌는 장면(fun)과 감성 장면(mood) 후보를 고르고 candidates.json과 리뷰 카드를 만들 때 사용합니다. 후보마다 원본 구간, 선정 이유, 편집 계획, 기대 화면을 사용자에게 보여주고 선택을 받습니다.
---

# vlog-scout

목표 비율은 감성 90 · 재미 10입니다. 시간 quota가 아니라 흐름의 방향입니다. 감성 장면이 흐름을 이끌고, 재미는 실제로 웃긴 순간이 있을 때만 짧게 둡니다. 사용자는 **기대 화면**을 보고 고르므로, 카드마다 편집 후 모습이 분명해야 합니다.

## 1. 읽는 순서 (context 아끼기)

1. `work/<run>/analysis/index.md`: 클립 목록, 전사 여부, 웃음 후보 수
2. 클립별 `analysis/<id>/summary.md`: 대사(타임코드), 소리 이벤트, 정적, 장면 전환, contact sheet 시간 범위
3. 필요한 구간의 contact sheet(`sheet-NNN.jpg`, 2초 간격, 6×5, 왼쪽 위부터)만 이미지로 봅니다. 영상 전체나 원본은 열지 않습니다.
4. 사진은 `analysis/photos/sheet-*.jpg`와 `index.md`의 사진 목록을 봅니다.

## 2. 고르는 기준

**fun (소소한 재미)**
- setup → payoff → reaction이 보이는 구간. 예: 길 잃기, 계획 실패, 예상과 다른 음식, 서로 놀리기, 리액션
- `reaction` 소리 이벤트는 대사 밖의 큰 소리라는 신호일 뿐입니다. 대사와 화면으로 이유를 확인합니다.
- 대사 직후의 웃음, 같은 상황의 반복, 반전이 강한 근거입니다.
- 웃음의 앞뒤 맥락을 자르지 않습니다. 정적은 줄이되(예: 3초 → 1.2초) 없애지 않습니다.

**mood (여행 감성)**
- 풍경·이동·빛·음식·조용한 순간, 생활소음이 좋은 구간을 고릅니다.
- 내레이션을 얹을 장면은 4–10초로 넉넉하게 두고, 문장의 권장 읽기 시간에 맞춥니다.

**공통**
- `의심` 표시된 전사는 대사 근거로 쓰지 않습니다.
- 확인할 수 없는 행동·감정을 사실처럼 쓰지 않습니다. 불확실하면 `reason`에 적습니다.
- 원본 10분당 후보 5–10개를 목표로 하되, 근거 없는 후보를 채우지 않습니다.

## 3. candidates.json 쓰기

`work/<run>/candidates.json`에 씁니다. 형식은 [docs/workflow.md](../../../docs/workflow.md)에 있고, 예시는 다음과 같습니다.

```json
{"look": {"grade": "warm", "grade_strength": 0.5, "grain": 0.08, "vignette": 0.2, "letterbox": null},
 "candidates": [
  {"id": "c01", "title": "바람 부는 산책길", "tag": "mood", "source": "v003", "range": [192.0, 200.0],
   "reason": "빛과 흔들리는 나뭇잎, 대사 없이 길이 이어지는 구간", "evidence": ["v003 contact sheet 03:12–03:20"],
   "key_moment": 4.0, "preview": true,
   "plan": {"cuts": [[192.0, 200.0]], "speed": 1.0, "zoom": 1.0, "drift": true,
            "captions": [{"kind": "narration", "text": "오늘은 조금 천천히 걷기로 했다\n바람이 먼저 와 있었다",
                          "at": 0.5, "duration": 5.5, "position": "lower_left", "sub": "a slow day"}],
            "bgm": {"asset": "bgm-walk", "gain_db": -20, "note": "현장음을 가리지 않게 낮게"},
            "notes": ["현장음의 목소리 포함 여부는 별도 청취 확인"]}}]}
```

- `range`·`cuts`는 원본(proxy) 기준 초입니다. `key_moment`·자막 `at`·효과음 `at`은 편집 후 기준 초입니다.
- `key_moment`에는 기대 화면 still로 보여줄 가장 웃긴(또는 아름다운) 순간을 둡니다.
- `preview: true`는 상위 5개 정도와 움직임이 중요한 후보에만 둡니다. 렌더 시간이 듭니다.
- `look`은 `candidates.json` 최상위에 선택적으로 둡니다. 영상 전체에 하나이며 후보별 `plan`에는 넣지 않습니다.
- 연출 필드(편집 후 기준 초):
  - `transition: "dissolve"`: 장소·시간 전환에만. 후보 카드에는 표시만 하고 조립 뒤 화면을 확인합니다.
  - `drift: true`: 영상의 느린 줌. 사진은 기존 줌을 쓰므로 지정하지 않습니다.
  - `effects`: `[{"type": "punch_zoom"|"shake"|"flash"|"speedlines"|"light_leak", "at": 4.5, "duration": 0.6, "strength": 1}]` 예능 효과는 반전·리액션에, `light_leak`은 감성 장면 전환에 드물게 씁니다(최소 0.5초).
  - `inserts`: 사진 한 장은 `{"photo": "p053", "at": 1.0, "duration": 3.0, "position": "right"}`. "사진 엄청 찍음" 같은 장면은 `{"photos": ["p053", "p054", "p061"], "at": 1.0, "duration": 3.5, "interval": 0.3, "position": "center", "sfx": "sfx-shutter"}`처럼 여러 장을 셔터음과 함께 쌓습니다.
  - `bgm_options`: 비교할 BGM 2–4곡(`vlog-sound` 참고)
  - 자막 `sub`(감성 보조 문장), `sync`(`speech`/`manual`): [자막 가이드](../../../docs/caption-style.md)의 타이밍 절
- 대사 자막의 시각은 리뷰 때 단어 단위 전사로 자동 보정됩니다. 오래된 run에 `words.json`이 없으면 먼저 `python3 scripts/analyze.py --run-id <run> --add-words`를 실행합니다.
- 자막은 `k-mood-caption`, 음원은 `vlog-sound`를 따릅니다.
- 예시의 `bgm-walk`는 형식 예시입니다. `asset`에는 `python3 scripts/audio_library.py check`에서 `usable: true`인 ID만 씁니다.
- 쓸 수 있는 음원이 없으면 효과음은 `{"name": "띠용", "at": 4.5}`처럼 `asset`을 빼고, BGM은 `"bgm": "가볍게 걷는 템포"`처럼 문자열로 계획만 적습니다.
- 컷 길이·속도·줌을 바꿔 달라는 요청은 `candidates.json`의 `plan`을 고치고 리뷰를 다시 만듭니다. 결정은 그대로 `adopt`로 둡니다.

## 4. 리뷰와 선택

1. `python3 scripts/review.py build --run-id <run>`을 실행합니다. 검증 오류가 나면 그대로 고쳐 다시 실행합니다.
2. 사용자에게 다음을 알립니다.
   - `open work/<run>/review/vN/index.html`
   - 후보 수(fun/mood), 자막 비율, 확인이 필요한 점
3. 답을 기다립니다. 예: `c01 채택`, `c03 자막 수정: 띠용 말고 엥?`, `c05 제외`, 순서 지정
4. 답을 `selection.json`으로 옮깁니다.

```json
{"decisions": {"c01": {"decision": "adopt"},
               "c02": {"decision": "caption_edit", "note": "띠용 말고 엥?"},
               "c03": {"decision": "drop"}},
 "order": ["c02", "c01"]}
```

   - `decisions`에는 모든 후보가 정확히 한 번씩 들어갑니다.
   - `order`는 생략하면 촬영 순서입니다. 쓰면 `drop`이 아닌 후보를 **모두** 정확히 한 번씩 넣어야 합니다. 사용자가 "c05를 맨 앞에"처럼 일부만 말하면, 나머지는 촬영 순서로 채운 전체 순서를 만들어 확인받습니다.
   - 자막 수정 뒤 다시 선택할 때, 수정하지 않은 후보는 사용자가 이미 내린 결정을 그대로 가져옵니다. 고친 후보만 다시 묻습니다.
5. `python3 scripts/review.py select --run-id <run>`으로 기록합니다.
6. `caption_edit`가 있으면 `k-mood-caption`으로 고친 뒤 리뷰를 다시 만들고 다시 선택받습니다.

사용자가 언급하지 않은 후보를 임의로 채택하거나 제외하지 않습니다. 빠진 후보가 있으면 물어봅니다.
