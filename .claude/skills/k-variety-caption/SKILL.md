---
name: k-variety-caption
description: vlog-me 후보나 timeline에 예능 80 · 감성 20 스타일의 한국어 자막을 쓰거나 고칠 때 사용합니다. 받아치기·상황·효과 글자·속마음·감성·장소 자막의 kind와 preset을 고르고, 사용자의 자막 수정 요청을 반영합니다.
---

# k-variety-caption

기준 문서는 [docs/caption-style.md](../../../docs/caption-style.md)이고, preset과 글자 수 제한은 `renderer/src/production/presets.json`입니다. 문서와 이 Skill이 다르면 문서를 따릅니다.

## 쓰는 순서

1. 장면의 웃음 구조를 먼저 적습니다: setup(무슨 상황) → payoff(반전) → reaction(반응). 사물 의인화, 내레이터 해설, 자막 연쇄 같은 예능 화법과 효과(`effects`)를 함께 고려합니다(가이드의 "예능 화법").
2. 자막을 그 시간에 맞춰 배치합니다.
   - setup: `situation`(사실만). 예: `같은 골목 3바퀴째`
   - payoff 순간: `sfx_text` 하나. 예: `띠용?!`
   - reaction: `variety` 받아치기 또는 `inner_voice` 속마음. 예: `결국 원점`, `(기억력 테스트 실패)`
   - 실제 대사를 살릴 때만 `dialogue`
3. 감성 장면에는 `mood` 한 줄 또는 `place` 하나만 둡니다. 효과 글자는 넣지 않습니다.
4. 리뷰 페이지 머리의 자막 비율(목표 예능 80%)을 확인합니다. 비율을 맞추려고 웃기지 않은 장면에 예능 자막을 붙이지 않습니다.

## 체크리스트

- [ ] kind마다 글자 수 안(받아치기 18자, 효과 글자 8자 등), 최대 2줄
- [ ] 한 화면에 예능 자막 3개 이하, 효과 글자 1개
- [ ] payoff 전에 결말을 자막으로 먼저 말하지 않음
- [ ] `dialogue`는 전사·화면으로 확인한 실제 대사뿐. `의심` 구간은 쓰지 않음
- [ ] 외모·체형·말투 조롱 없음. 같이 여행한 사람이 보고 웃을 수 있는 수위
- [ ] 위치가 얼굴과 대사 자막을 가리지 않음(기대 화면 still로 확인)
- [ ] preset을 장면 성격에 맞게 바꿔 씀(같은 preset 3연속 금지, 상단 박스는 색·모양 variation)
- [ ] 대사 자막 타이밍은 리뷰 카드의 "발화에 맞춤" 결과를 확인. `주의`가 뜨면 직접 고침
- [ ] 감성 자막은 `editorial`·`letter-fade`·`film-line`·`place-editorial`과 `sub`로 정돈된 미감을 줌

## 좋은 예와 나쁜 예

| 장면 | 좋은 예 | 나쁜 예 |
| --- | --- | --- |
| 지도 앱을 또 켬 | `situation` 지도 앱 4번째 재검색 → `variety` 길치 인증 | `variety` 진짜 너무너무 웃긴 상황 ㅋㅋㅋ (설명만 길고 받아치기가 아님) |
| 음식이 생각보다 매움 | `sfx_text` 화끈 → `inner_voice` (괜히 시켰다) | `dialogue` "이거 진짜 맵다" (실제로 말하지 않음) |
| 노을 해변 | `mood` 그래도 바람은 좋았다 | `variety` 감성 폭발!! (감성 구간에 예능 자막) |

## 사용자가 자막 수정을 요청했을 때

1. `selection.json`의 `note`를 읽고 해당 후보의 `plan.captions`만 고칩니다. 다른 후보는 건드리지 않습니다.
2. `python3 scripts/review.py build --run-id <run>`으로 새 리뷰 버전을 만들고, 고친 카드의 기대 화면을 보여줍니다.
3. 다시 선택을 받아 `review.py select`로 기록합니다.

조립 뒤 `timeline.json`의 자막을 직접 고칠 때도 같은 기준을 따릅니다. timeline에서는 `preset`을 생략할 수 없습니다. 고친 뒤 `python3 scripts/render_prod.py --run-id <run> --check`로 검증합니다.
