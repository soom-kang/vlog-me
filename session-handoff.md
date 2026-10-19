# Session Handoff

## Current Objective

Claude Code 단독·기존 Skills 우선 기반 환경의 Studio agent·편집 문제를 해결했습니다. native Studio 대신 완료된 합성 영상만 재생하는 읽기 전용 뷰어를 사용합니다. 최신 근거는 reports/preview-only-review.md입니다.

## Startup

```bash
cd /Users/soom.kang/Desktop/work/2.services/vlog-me
./scripts/claude.sh
```

`init.sh`는 Claude Code 안에서 실행합니다([시작 안내](docs/getting-started.md)). CLAUDE.md·progress.md·feature_list.json을 읽고 현재 요청 범위만 수행합니다. init.sh는 설치·원본 처리·음원 다운로드·model 호출을 하지 않습니다.

## Preview and Recovery

```bash
python3 scripts/synthetic.py status --run-id synthetic-20261019-062743-ee85e59d
./scripts/studio.sh synthetic-20261019-062743-ee85e59d
```

출력된 127.0.0.1 URL을 열고 확인 후 Ctrl-C로 종료합니다. npm studio alias도 같은 helper입니다. agent·편집·설치·render UI/API가 없으며 viewer는 state·props·출력을 변경하지 않습니다. 완료·hash 검증을 통과한 128 MiB 이하 합성 영상 snapshot만 읽습니다.

live --refresh는 제거되어 exit 2로 종료합니다. pending run은 Claude Code에서 timeline 수정 후 renderer로 완료하고, 새 succeeded run을 엽니다. 완료 run을 덮어쓰거나 fingerprint를 수동 갱신하지 않습니다. 코드 변경 후 과거 PASS run의 stale은 정상입니다. 실패·paused·lock·partial은 보존하고 자동 삭제하지 않습니다.

새 합성 검증은 ./scripts/smoke-render.sh --seconds 4로 시작합니다. 영상 4초와 사진 2초를 생성하며 본편 길이 제한이 아닙니다. localhost와 browser 실행 권한이 필요합니다.

## Verified

- Python 104개·Node 2개·lint·typecheck: 2026-10-19 `./init.sh` PASS(production 계약 포함). 이전 기록: reports/preview-only-checks.log.
- 최종 6초 렌더·HTTP 23건·상태/파일 보존·SIGTERM 종료: reports/preview-only-lifecycle.json.
- 실제 브라우저 무음 재생·탐색: reports/preview-only-browser.json 및 preview-only-viewer.png.
- 현재 검증용 server와 tab은 종료했습니다.
- 원본·음원·ASR·플랫폼·사람 청취는 NOT_RUN입니다.

## Changes in This Turn

- scripts/studio.py: 읽기 전용 viewer로 교체.
- renderer/package.json: studio alias를 같은 helper로 변경; dependency/lock 변경 없음.
- tests/test_studio.py: 제거한 native Studio 동작 대신 preview·실패·HTTP 경계 검사.
- README.md·CLAUDE.md·docs/workflow.md·feature tracker·진행/인수인계·reports 갱신.
- official Skill·config·renderer 구현·원본 설계·이전 artifact는 보존했습니다.

## Next Permitted Action

현재 결과를 설명하거나 합성 fixture를 검증할 수 있습니다. production 계약(단위 1)은 구현했고 phase는 바꾸지 않았습니다. 단위 2(Ingest), 단위 3(Analyze), 단위 4(후보 카드·기대 화면), 단위 5(자막 preset·번들 폰트), 단위 6(사운드), 단위 7(조립·롱폼 렌더)은 합성 fixture로 검증했습니다(`./scripts/smoke-media.sh`). Whisper 모델은 `.tools/whisper/ggml-large-v3-turbo.bin`입니다. 자막은 [자막 가이드](docs/caption-style.md)를 따릅니다. 사운드는 [사운드 가이드](docs/sound-guide.md)를 따릅니다. 렌더는 `production_render: true`가 있어야 실행됩니다. 다음은 [로드맵](docs/roadmap.md) 단위 8(Skill·harness)이며, 사용자가 명시적으로 요청할 때만 시작합니다. 원본 보호 hook(`.claude/hooks/protect_sources.py`)이 `sources/` 쓰기를 막습니다. 원본 접근·음원 다운로드·실제 본편 렌더·업로드를 시작하지 않습니다. 범위 밖 native Remotion Studio 명령으로 우회하지 않습니다. commit·push·전역 설정 변경도 명시 요청 없이 수행하지 않습니다(이 폴더는 Git 저장소입니다).
