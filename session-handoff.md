# Session Handoff

## Current Objective

2026-10-22 (최신): `mood-vlog-style`을 완료하고 병합했습니다(`95259e0`, Orca Run run_35eda3424ac5, 상태 파일 `.orca-runs/run_35eda3424ac5.md`). 감성 90 · 예능 10, 내레이션 자막, 감성 preset 10개, look·light_leak·dissolve·drift가 들어갔고, 자막 Skill은 `k-mood-caption`입니다. 다음 허용 행동은 둘입니다. (1) 사용자가 동의하면 갤러리 still 두 장을 만듭니다: `node renderer/scripts/gallery.mjs reports/caption-gallery-v2.jpg`, `node renderer/scripts/gallery.mjs reports/look-gallery.jpg LookGallery`. 기존 caption-gallery.jpg는 덮어쓰지 않습니다. 사용자가 보고 크기·위치·톤을 조정합니다. (2) 영상 편집·렌더는 사용자가 따로 요청할 때 `/vlog-workflow`로 시작합니다. 기존 prod run의 timeline은 고치지 않았습니다. 정리할 것: worktree `/Users/soom.kang/orca/workspaces/vlog-me/orca-mood-vlog-style`과 브랜치 `soom-kang/orca-mood-vlog-style`은 사용자 확인 뒤 지웁니다. Orca new-child는 origin/main에서 만들어지므로 다음부터 `--base-branch main`을 씁니다. 근거: reports/mood-vlog-style.md.

2026-10-22: 개발 작업 전용 Orca 흐름(`orca-dev-orchestration`)을 구현했습니다. 운영 절차는 `docs/orca.md`, Codex 규칙은 `AGENTS.md`, 근거는 reports/orca-dev-orchestration.md입니다. production은 그대로 Claude 단일 세션입니다. vlog-me는 Orca repo로 등록했고(2026-10-22), 실패 receipt 확인도 마쳤습니다(reports/orca-spike-2026-10-22.md 3번). 남은 일: 사용자의 `orca.yaml` 승인, 첫 실제 Orca Run(사용자가 기능을 지정할 때). `first-real-sample`은 on_hold이며, 재개는 사용자 결정입니다.

이전 목표(보류 중):
첫 실제 sample(`sources/vietnam-20260527/`)을 후보 리뷰까지 진행했습니다. run `prod-20261019-075246-e19437c2`는 `reviewed/pending`이며 사용자 선택을 기다립니다. 근거는 reports/first-sample-review-2026-10-19.md입니다.

- phase: production (`config/project.json`), `.claude/settings.json`의 `sources/` 읽기 deny 해제(쓰기 deny·hook 유지)
- 최종 렌더 완료(`rendered/succeeded`): `work/prod-20261019-075246-e19437c2/render/v3/final.mp4` (56.9초, -14.16 LUFS, -2.1 dBTP). 노을 BGM은 Mixkit Serene View(Arulo). 크레딧 `render/v3/credits.md`. 렌더·음원 플래그는 모두 false. v1·v2는 보존

## Startup

```bash
cd /Users/soom.kang/Desktop/work/2.services/vlog-me
./scripts/claude.sh
```

`init.sh`는 Claude Code 안에서 실행합니다([시작 안내](docs/getting-started.md)). CLAUDE.md·progress.md·feature_list.json을 읽고 현재 요청 범위만 수행합니다. init.sh는 설치·원본 처리·음원 다운로드·model 호출을 하지 않습니다.

## Preview and Recovery

```bash
python3 scripts/synthetic.py status --run-id synthetic-20261019-064243-1f9751cd
./scripts/studio.sh synthetic-20261019-064243-1f9751cd
```

출력된 127.0.0.1 URL을 열고 확인 후 Ctrl-C로 종료합니다. npm studio alias도 같은 helper입니다. agent·편집·설치·render UI/API가 없으며 viewer는 state·props·출력을 변경하지 않습니다. 완료·hash 검증을 통과한 128 MiB 이하 합성 영상 snapshot만 읽습니다.

live --refresh는 제거되어 exit 2로 종료합니다. pending run은 Claude Code에서 timeline 수정 후 renderer로 완료하고, 새 succeeded run을 엽니다. 완료 run을 덮어쓰거나 fingerprint를 수동 갱신하지 않습니다. 코드 변경 후 과거 PASS run의 stale은 정상입니다. 실패·paused·lock·partial은 보존하고 자동 삭제하지 않습니다.

새 합성 검증은 ./scripts/smoke-render.sh --seconds 4로 시작합니다. 영상 4초와 사진 2초를 생성하며 본편 길이 제한이 아닙니다. localhost와 browser 실행 권한이 필요합니다.

## Verified

- Python 112개·Node 2개·lint·typecheck: 2026-10-19 `./init.sh` PASS(production 계약 포함). 이전 기록: reports/preview-only-checks.log.
- 최종 6초 렌더·HTTP 23건·상태/파일 보존·SIGTERM 종료: reports/preview-only-lifecycle.json.
- 실제 브라우저 무음 재생·탐색: reports/preview-only-browser.json 및 preview-only-viewer.png.
- 현재 검증용 server와 tab은 종료했습니다.
- 원본·음원·ASR·플랫폼·사람 청취는 NOT_RUN입니다.

## Changes in This Turn

- config/project.json·.claude/settings.json: production 전환(위 참고)
- scripts/analyze.py: contact sheet `fps` 필터에 `eof_action=pass`(1초 미만 클립 실패 수정). 첫 실패 분석은 `analysis.failed-20261019-075815/`로 보존
- work/prod-20261019-075246-e19437c2/: ingest·analyze·candidates.json·review v1–v3
- feature_list.json(first-real-sample, in_progress)·progress.md·reports/first-sample-review-2026-10-19.md·reports/README.md

## Next Permitted Action

2026-10-21 (본편 렌더): run `prod-20261020-053818-932c04b5`는 rendered/succeeded입니다. 최종본은 `render/v1/final.mp4`, 크레딧은 `render/v1/credits.md`(설명란용), 샘플은 `review/sample-v10.mp4`입니다. `production_render`는 다시 false로 돌렸습니다. 실패한 첫 결과물은 `render/v1/final.failed-truepeak.partial.mp4`로 보존했습니다. 다음은 사용자 시청이고, 작은 수정은 timeline.json → `render_prod.py --check` → 렌더 순서로 합니다(렌더는 동의가 필요). commit은 하지 않았습니다.

2026-10-21 (선택 확정): run `prod-20261020-053818-932c04b5`는 selected/pending입니다(채택 42, 삭제 c07 c11 c17 c32 c34 c39 c40 c42, order는 selection.json에 있음). 최신 리뷰는 v9, 샘플은 `review/sample-v9.mp4`입니다. v8(대사 사이 편집)은 사용자 판단으로 버렸고 리뷰 폴더만 보존했습니다. 블러 배경 proxy는 `proxy/fill/<id>-v2.mp4`(시간 평균)를 쓰고, 이전 `<id>.mp4`는 보존했습니다. 남성 음역 경고 c15(사용자가 살려 달라고 한 문장), c48은 청취 확인이 필요합니다. 다음 허용 행동: 사용자 요청 시 `assemble.py` → `production_render: true` 동의 후 `render_prod.py`.

2026-10-20 (본편 v2 피드백 3차): 리뷰 v8과 `review/sample-v8.mp4`가 최신입니다. 선택은 아직 기록하지 않았습니다(사용자 답이 수정 요청만 담고 있었음). 원음 방침은 이렇습니다. 남성 목소리가 그녀 말과 겹치지 않으면 컷을 편집하고, 겹치면 짧게 뮤트하고, 정말 안 되는 7개 후보(c03·c09·c21·c33·c37·c38·c42)는 원음을 끄고 자막으로 처리합니다. `work/<run>/proxy/stab/v130.mp4`는 보정 실험에서 남은 파생 파일입니다(사용하지 않음).

2026-10-20 (본편 v2 피드백 2차): 리뷰 v7과 `review/sample-v7.mp4`가 최신입니다. 원음 방침은 이렇습니다. 대사 후보는 `dialogue_only`로 말한 구간에서만 원음이 들리고, c03·c09·c21·c33·c37·c38·c42는 원음을 끕니다. 수동 mute 목록은 candidates.json에 있습니다. BGM은 장마다 `bgm.offset`으로 이어지고, 콜드 오픈은 sunset-dream 90초 지점부터 씁니다. 남성 음역 경고는 c40·c48이 남았습니다. 샘플은 후보 경계마다 BGM 페이드가 있고, c14→c15 장 전환에서 0.8초 무음이 생깁니다. 다음 허용 행동은 사용자 선택 기록입니다.

2026-10-20 (본편 v2 피드백): 리뷰 v5와 `review/sample-v5.mp4`를 만들었습니다. 샘플은 리뷰 미리보기를 스토리 순서로 이어 붙인 확인용이고, production 렌더가 아닙니다. 곡이 후보마다 처음부터 시작합니다. 추천 순서(selection `order`): c01 c02 c05 c03 c04 c06 c07 c08 c09 c10 c11 c12 c13 c14 c15 c16 c17 c18 c19 c20 c21 c22 c23 c24 c26 c27 c25 c28 c29 c31 c30 c32 c33 c34 c35 c36 c37 c38 c39 c40 c41 c42 c43 c44 c46 c47 c45 c48 c50 c49. 원음 방침(대사 후보 dialogue_only, 나머지 -80 dB)과 대사 안의 수동 mute는 candidates.json에 적혀 있습니다. 남성 음역 경고가 남은 c40·c42·c48은 잡음으로 판단했지만 청취 확인이 필요합니다. 다음 허용 행동은 사용자 선택을 기록하는 것입니다.

2026-10-20 (본편 v2): 추가 폴더 `additional/`(영상 120개)를 포함해 새 run `prod-20261020-053818-932c04b5`를 만들었습니다. 후보 50개, 리뷰 `review/v3/index.html`이 있고, 사용자 선택을 기다리는 중입니다. v2는 후보 수정 중 실수로 시작된 빌드인데 지우지 않고 보존했습니다. 이전 run의 확정 17개는 영상·사진 ID가 같아서 그대로 옮겼습니다. 다만 c18(구 오프닝)의 장소 자막은 "오후 3시, 인피니티 풀"로 바꿨습니다. 추천 순서는 c01(콜드 오픈)을 맨 앞에 두고 나머지는 촬영 순서입니다. selection.json에 `order`로 기록해야 합니다. 대사 자막은 전사와 음높이로 판정한 것이라 사람이 듣고 확인해야 합니다. 남자 출연자 판정은 프레임과 음높이 기준이며, 동행의 손·시계·팔이 나오는 구간은 뺐습니다. 다음 허용 행동은 사용자 선택을 기록하는 것(`review.py select`)입니다. 조립·렌더는 요청할 때만 합니다.

2026-10-20: `./init.sh`가 production에서도 동작하도록 harness를 고쳤습니다. 이어서 첫 sample 피드백을 반영했습니다(대사 자막 목소리 구간 타이밍, preset 33종, 효과, 사진 쌓기, BGM 비교). 최종본은 `work/prod-20261019-075246-e19437c2/render/v4/final.mp4`(56.9초, -14.22 LUFS, QA PASS)이고 사용자가 2026-10-20 승인했습니다("lgtm"). 2026-10-20 본편 후보 17개(약 87초)를 같은 run에 만들었습니다(이전 sample 후보는 candidates.prev-*). 사용자가 리뷰 v17·v18을 보고 17개 전부 채택했습니다(selection.json, 이전 sample 선택은 selection.sample-v4.json). c03 자막은 "오늘 찍은 사진: 약 2억 장", 세로 사진은 CSS 블러 배경(BlurBackdrop), 세로 영상은 블러 배경을 구운 proxy(`review.filled`, `proxy/fill/<id>.mp4`)를 씁니다. 상태는 selected/pending. 다음 허용 행동: 사용자가 요청하면 `assemble.py`(기존 sample timeline은 timeline.prev-*로 밀림) → `production_render: true` 동의 후 `render_prod.py`(render v5). 원칙: 남자 출연자의 목소리·등장·동행 암시는 모두 제외합니다. 리뷰 v12(실패)는 보존했습니다. production_render·audio_search·audio_downloads는 false입니다. 자막·음량 같은 작은 수정은 timeline.json → `render_prod.py --check` → 렌더(`production_render: true` 동의 필요). 장면을 넣거나 빼려면 리뷰부터 다시 합니다. 무음 26.5초 해결에는 음원 등록 또는 승인된 다운로드가 필요합니다. 원칙: 남자 출연자의 목소리·등장 장면·동행 암시는 모두 편집합니다(사용자 지시). 자막 수정이 있으면 `k-variety-caption`으로 고치고 리뷰를 다시 만듭니다. 조립(`assemble.py`)·렌더(`production_render: true` 필요)·음원 탐색/다운로드(`audio_search`/`audio_downloads`)는 사용자가 각각 요청할 때만 시작합니다. 대사 자막은 전사 기반이라 사람 청취 확인이 필요합니다.

현재 config가 production이므로 합성 scope 테스트 16개(test_contracts·test_recovery·test_studio)는 scope 거부로 실패합니다. 합성 검증이나 전체 테스트는 config/project.json과 .claude/settings.json을 git의 setup 설정으로 되돌린 뒤 실행합니다(두 phase는 동시에 쓸 수 없음). 알려진 개선 후보: 사진 contact sheet 번호 어긋남·마지막 묶음 누락, 세로 사진 좌우 여백, doctor의 `asr: NOT_INSTALLED` 판정. commit·push는 요청 시에만 합니다.
