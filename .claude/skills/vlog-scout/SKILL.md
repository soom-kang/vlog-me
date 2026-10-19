---
name: vlog-scout
description: 분석이 끝난 vlog-me run에서 재밌는 장면(fun)과 감성 장면(mood) 후보를 고르고 candidates.json과 리뷰 카드를 만들 때 사용합니다. 후보마다 원본 구간, 선정 이유, 편집 계획, 기대 화면을 사용자에게 보여주고 선택을 받습니다.
---

# vlog-scout

목표 비율은 재미 60 · 감성 40입니다. 시간 quota가 아니라 흐름의 방향입니다. 재미 장면이 흐름을 이끌고, 이동·풍경·마무리에 감성 호흡을 둡니다. 사용자는 **기대 화면**을 보고 고르므로, 카드마다 편집 후 모습이 분명해야 합니다.

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
- 풍경, 이동, 노을, 음식 클로즈업, 조용한 순간. 장면 전환이 적고 대사가 없는 구간
- 감성 구간은 짧게(3–8초) 두고 현장음을 살립니다.

**공통**
- `의심` 표시된 전사는 대사 근거로 쓰지 않습니다.
- 확인할 수 없는 행동·감정을 사실처럼 쓰지 않습니다. 불확실하면 `reason`에 적습니다.
- 원본 10분당 후보 5–10개를 목표로 하되, 근거 없는 후보를 채우지 않습니다.

## 3. candidates.json 쓰기

`work/<run>/candidates.json`에 씁니다. 형식은 [docs/workflow.md](../../../docs/workflow.md)에 있고, 예시는 다음과 같습니다.

```json
{"candidates": [
  {"id": "c01", "title": "같은 골목 3바퀴", "tag": "fun", "source": "v003", "range": [192.0, 221.0],
   "reason": "대사 직후 reaction, 같은 골목 프레임 반복", "evidence": ["v003 reaction 03:31", "대사 03:20"],
   "dialogue": "여기 아까 왔던 데 아니야?", "key_moment": 5.0, "preview": true,
   "plan": {"cuts": [[192.0, 200.0], [203.5, 208.0]], "speed": 1.0, "zoom": 1.2,
            "captions": [{"kind": "situation", "text": "같은 골목 3바퀴째", "at": 0.0, "duration": 3.0, "position": "upper_left"},
                         {"kind": "sfx_text", "text": "띠용?!", "at": 4.5, "duration": 1.0, "position": "upper_right"}],
            "sfx": [{"name": "띠용", "at": 4.5, "asset": "sfx-boing"}],
            "bgm": {"asset": "bgm-walk", "gain_db": -16, "note": "가볍게"},
            "notes": ["정적 3초 → 1.2초"]}}]}
```

- `range`·`cuts`는 원본(proxy) 기준 초입니다. `key_moment`·자막 `at`·효과음 `at`은 편집 후 기준 초입니다.
- `key_moment`에는 기대 화면 still로 보여줄 가장 웃긴(또는 아름다운) 순간을 둡니다.
- `preview: true`는 상위 5개 정도와 움직임이 중요한 후보에만 둡니다. 렌더 시간이 듭니다.
- 자막은 `k-variety-caption`, 음원은 `vlog-sound`를 따릅니다.
- 예시의 `sfx-boing`·`bgm-walk`는 형식 예시입니다. `asset`에는 `python3 scripts/audio_library.py check`에서 `usable: true`인 ID만 씁니다.
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
6. `caption_edit`가 있으면 `k-variety-caption`으로 고친 뒤 리뷰를 다시 만들고 다시 선택받습니다.

사용자가 언급하지 않은 후보를 임의로 채택하거나 제외하지 않습니다. 빠진 후보가 있으면 물어봅니다.
