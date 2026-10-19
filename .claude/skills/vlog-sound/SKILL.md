---
name: vlog-sound
description: vlog-me 브이로그의 BGM·효과음을 고르고, 사용자 음원을 등록하거나 무료 음원을 찾아 승인 후 받을 때 사용합니다. 라이선스 근거 기록, 장면별 배치, ducking과 효과음 밀도 확인을 다룹니다.
---

# vlog-sound

기준 문서는 [docs/sound-guide.md](../../../docs/sound-guide.md)입니다. 권리 판단 원칙은 설계 8절을 따릅니다. 판정 결과는 선별 기록일 뿐 claim이 없다는 보증이 아닙니다.

## 1. 지금 쓸 수 있는 음원 확인

```bash
python3 scripts/audio_library.py check --platforms youtube
```

`usable: false`인 음원은 이유(`claim_pending` 등)와 함께 사용자에게 보고하고 쓰지 않습니다.

## 2. 사용자가 준 파일 등록

1. 파일이 `assets/audio/` 아래에 있는지 확인합니다. 없으면 어디에 두면 되는지 안내합니다.
2. 출처, 이용 조건, Content ID 관련 안내를 사용자에게 확인하거나 공식 페이지에서 확인합니다.
3. `python3 scripts/audio_library.py register ...`로 등록합니다. 근거가 부족하면 `--license-status pending` 또는 `--claim-status unknown`으로 등록해 보류합니다. 사람의 취향 승인으로 `unknown`을 바꾸지 않습니다.

## 3. 무료 음원 찾기 (요청이 있을 때만)

1. config의 `audio_search`가 `true`인지 확인합니다. `false`면 켜자고 제안할 수 있지만, 사용자가 동의하기 전에는 바꾸지도 찾지도 않습니다.
2. 장면 묶음별로 필요한 역할을 정합니다. 예: 도입은 `bright`, 헤매는 장면은 `silly`, 마무리는 `warm`, 효과음은 `boing`·`pop`·`whoosh`
3. 공식 공급처에서 후보를 찾고, 다음 표로 보여줍니다.

| 용도 | 제목·제작자 | 공급처 URL | 이용 조건 URL | Content ID 근거 | 길이·크기 |
| --- | --- | --- | --- | --- | --- |

4. 사용자가 고른 파일만 받습니다. `audio_downloads: true`가 필요합니다. 받을 곳은 `assets/audio/library/`이고, 공식 다운로드 경로만 씁니다.
5. `--origin claude_search`로 등록합니다.

공급처 이름이나 "no copyright"라는 제목만으로 안전하다고 판단하지 않습니다. 근거를 찾지 못하면 `pending`으로 둡니다.

## 4. 배치

- BGM은 장면 묶음마다 한 곡을 씁니다. 같은 BGM을 쓰는 연속 후보는 조립할 때 한 곡으로 이어집니다.
- 기본 -16 dB이고, 대사 구간은 자동으로 12 dB 낮아집니다.
- 효과음은 payoff·reaction에만 씁니다. 1분에 8개 이하, 같은 효과음은 3초 안에 반복하지 않습니다.
- 감성 구간은 현장음 위주로 두고 효과음을 넣지 않습니다.
- 후보 카드: `plan.sfx[].asset`, `plan.bgm.asset`에 등록 ID를 넣으면 미리보기에 소리가 들어갑니다.

## 5. 확인

- 리뷰 카드나 `assemble-report.md`에 `주의`가 있으면 사용자에게 알립니다.
- 렌더 후 `render/vN/credits.md`의 표기 문구를 사용자에게 전달합니다(영상 설명란용).
- 효과음 타이밍, 반복 피로, ducking의 자연스러움은 사용자가 듣고 판단합니다. 듣지 않은 것을 청취 완료로 보고하지 않습니다.
