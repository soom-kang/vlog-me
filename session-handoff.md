# Session Handoff

## Current Objective

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

2026-10-20: `./init.sh`가 production에서도 동작하도록 harness를 고쳤습니다. 이어서 첫 sample 피드백을 반영했습니다(대사 자막 목소리 구간 타이밍, preset 33종, 효과, 사진 쌓기, BGM 비교). 최종본은 `work/prod-20261019-075246-e19437c2/render/v4/final.mp4`(56.9초, -14.22 LUFS, QA PASS)이고 사용자 시청 대기 중입니다. 리뷰 v12(실패)는 보존했습니다. production_render·audio_search·audio_downloads는 false입니다. 자막·음량 같은 작은 수정은 timeline.json → `render_prod.py --check` → 렌더(`production_render: true` 동의 필요). 장면을 넣거나 빼려면 리뷰부터 다시 합니다. 무음 26.5초 해결에는 음원 등록 또는 승인된 다운로드가 필요합니다. 원칙: 남자 출연자의 목소리·등장 장면·동행 암시는 모두 편집합니다(사용자 지시). 자막 수정이 있으면 `k-variety-caption`으로 고치고 리뷰를 다시 만듭니다. 조립(`assemble.py`)·렌더(`production_render: true` 필요)·음원 탐색/다운로드(`audio_search`/`audio_downloads`)는 사용자가 각각 요청할 때만 시작합니다. 대사 자막은 전사 기반이라 사람 청취 확인이 필요합니다.

현재 config가 production이므로 합성 scope 테스트 16개(test_contracts·test_recovery·test_studio)는 scope 거부로 실패합니다. 합성 검증이나 전체 테스트는 config/project.json과 .claude/settings.json을 git의 setup 설정으로 되돌린 뒤 실행합니다(두 phase는 동시에 쓸 수 없음). 알려진 개선 후보: 사진 contact sheet 번호 어긋남·마지막 묶음 누락, 세로 사진 좌우 여백, doctor의 `asr: NOT_INSTALLED` 판정. commit·push는 요청 시에만 합니다.
