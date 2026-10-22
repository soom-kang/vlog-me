# mood-vlog-style · 감성 90 · 예능 10 환경 (2026-10-22)

사용자 요청: 자막 비율을 예능 80 · 감성 20에서 감성 90 · 예능 10으로 바꾸고, 대사 없는 풍경 장면에서 자막만으로 이야기를 전하는 장면과 감성 자막 스타일·효과를 갖춥니다. 레퍼런스는 오눅(@onuk), 강민경(@iammingki)입니다. 환경 구성만 했고 영상 편집·렌더는 하지 않았습니다.

- 계획: [docs/superpowers/plans/2026-10-22-mood-vlog-style.md](../docs/superpowers/plans/2026-10-22-mood-vlog-style.md) (1절에 레퍼런스 조사, 확인/추정 구분)
- 흐름: Orca Run `run_35eda3424ac5`. plan(Claude opus) → 사용자 승인 → coding(Codex, child worktree) → dev-check → 독립 리뷰(Claude sonnet, 병합 가능, 참고 4건) → 수정 1회 → 병합 `95259e0`

## 바뀐 것

- 비율: `presets.json` `target_mood_share` 0.9, `share_window` [0.8, 1.0](감성 100%도 범위 안). 리뷰 페이지·조립 보고서는 감성 비율을 먼저 표시합니다. 보고용이며 강제하지 않습니다.
- 새 kind `narration`(group mood): 최대 4줄 × 22자. 줄이 차례로 나타나고, 최소 2.5초, 권장 읽기 시간보다 짧으면 경고를 냅니다.
- 새 preset 10개(합계 43개, 기존 33개는 모양 불변): `soft-caption`, `blur-in`, `bilingual`(한/영 병기), `diary`, `diary-center`, `letter`(손글씨), `typewriter`, `chapter`, `dialogue-soft`, `deadpan`. kind별 기본 preset은 감성 쪽으로 바꿨습니다.
- 화면 톤 `look`(timeline·candidates 최상위, 전역 하나): `warm`/`faded`/`film` 색감, grain, vignette, letterbox 2.0/2.39, 상한 검증. 없으면 이전과 같은 화면입니다.
- 효과: `light_leak`, 클립 `transition: "dissolve"`(원본 여유 검증, 소리는 컷 그대로), 영상 `drift`(느린 1.05배 줌).
- 갤러리: `CaptionGallery`에 내레이션 샘플, 새 `LookGallery` composition, `gallery.mjs <out> [LookGallery]`.
- Skill: `k-variety-caption` → `k-mood-caption`. vlog-scout·vlog-workflow·vlog-sound를 갱신하고 skills-lock hash도 갱신했습니다.
- 문서: caption-style.md 재작성(내레이션 작법·예문, look·효과 사용 기준), editorial·sound guide 톤, CLAUDE.md·README·roadmap·workflow.
- live `config/project.json`: `editorial_direction`, `caption_style` 두 값만 바꿨습니다(coordinator). phase·권한·audio·render 플래그는 그대로입니다.

## 검증

| 항목 | 결과 |
| --- | --- |
| worker worktree `./scripts/dev-check.sh` (수정 후 HEAD 5004860) | PASS: Python 180 실행, 7 skip(미디어 게이트) · Node 9 · lint · typecheck |
| main 병합 뒤 `./init.sh` | PASS |
| 독립 리뷰 | 병합 가능. 참고 3건(조립 시 내레이션 반올림, scout 예시 dissolve, Captions.tsx 이름 가림)은 수정 1회로 반영. 그 수정은 coordinator가 diff를 확인했고 재리뷰는 생략했습니다(리뷰 지적의 직접 수정, 83줄) |
| 테스트 약화 | 삭제된 assert는 모두 비율 계약 대체이거나 coordinator가 승인한 기본 preset 기대값(test_caption_text_rules, test_longform)입니다 |
| 원본·작업·음원 폴더 경로 추가 | 없음 |

## NOT_RUN과 한계

- 갤러리 still: 2026-10-22 PASS(`reports/caption-gallery-v2.jpg` 1920×11880, `reports/look-gallery.jpg` 1920×2160, frame 30). 사용자 피드백 대기. 내레이션 순차 등장·light leak 움직임·디졸브·drift·그레인 움직임은 still로 확인할 수 없습니다.
- 렌더: 합성 smoke, production은 NOT_RUN.
- 레퍼런스: 두 채널의 자막 폰트·위치·색보정은 출처로 확인하지 못해 추정입니다. 확인된 출처로 보면 강민경 채널은 예능식 편집이어서 "예능 10"과 `film` 톤에만 반영했습니다.
- 새 폰트는 넣지 않았습니다(승인된 OFL 7종만 사용). 구간별 look은 범위 밖입니다(사용자 결정: 전역만).
- 발견: Orca `new-child` worktree가 local main이 아니라 origin/main(994191d)에서 만들어졌습니다. worker가 0c2c094로 fast-forward해서 해결했습니다. 다음 Run부터는 `worker-start --base-branch main`을 쓰는 것이 좋습니다(docs/orca.md 보강 후보).
