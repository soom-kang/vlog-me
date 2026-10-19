# 미리보기 전용 전환 검증

기준일: 2026-10-19 · Asia/Seoul

**native Remotion Studio를 실행 경로에서 제거하고, 검증된 영상만 재생하는 읽기 전용 뷰어로 교체했습니다.** 기존 studio.sh 명령 이름은 유지했습니다. agent·편집 기능을 숨기는 방식 대신 해당 UI·backend를 아예 시작하지 않으며 새 dependency는 추가하지 않았습니다.

## 변경과 사용 방법

```bash
./init.sh
./scripts/claude.sh
```

편집과 렌더는 Claude Code에서 수행합니다. 성공한 합성 run을 확인할 때는 다음 명령을 사용합니다.

```bash
./scripts/studio.sh synthetic-20261018-151755-5c1016f2
```

출력된 http://127.0.0.1:PORT/ 주소를 브라우저에서 열고, 완료 후 terminal에서 Ctrl-C로 종료합니다. npm 경로인 `./scripts/npm.sh run studio -- RUN-ID`도 같은 helper를 실행합니다.

화면은 native video controls의 재생·탐색·음량·전체화면만 제공합니다. native Studio의 agent·코드 편집·설치·렌더·전사 API와 WebSocket은 없습니다. 직접 원본 경로나 임의 파일을 입력받지 않습니다. 공식 Skill 원문은 유지했으며 generic Studio 실행 예제보다 프로젝트 helper를 우선하도록 CLAUDE.md를 갱신했습니다.

기존 live --refresh는 명시적 오류로 종료합니다. 타임라인을 바꾸려면 Claude Code에서 새 pending 합성 run을 수정·렌더한 뒤 새 완료 run을 엽니다. 뷰어가 렌더·model을 자동 실행하지 않으며 기존 props·owner·영상·state를 수정하거나 삭제하지 않습니다. 이 변경으로 실시간 composition preview는 제공하지 않습니다.

## 구현 범위

- scripts/studio.py: 현재 scope와 run 상태·입력/출력 hash를 확인한 뒤 preview.mp4만 메모리에 읽습니다. pending·failed·paused·stale·lock·변조·alias는 거부합니다.
- HTTP는 127.0.0.1에만 bind합니다. 주소 역조회 없이 시작하고 GET·HEAD의 `/`, `/preview.mp4`만 제공합니다. 파일 서버·디렉터리 listing·임의 경로 읽기 기능은 없습니다.
- 영상 byte range를 지원하고 잘못된 range, 외부 Host·Origin, protocol upgrade, 쓰기 요청은 거부합니다. HTML에는 script·form·외부 resource가 없으며 CSP도 script 실행을 허용하지 않습니다.
- HTTP 요청은 검증된 메모리 snapshot만 읽습니다. 열어 둔 화면은 시작 당시 저장본이므로 실행 중 timeline 변경을 반영하지 않습니다.
- 128 MiB 한도는 합성 뷰어의 메모리 사용 범위이며 브이로그 완성본 길이 제한이 아닙니다.
- renderer/package.json의 studio alias도 동일 helper로 변경했습니다. dependency와 package-lock, renderer 구현은 그대로입니다.

Python 표준 라이브러리의 [HTTPServer/handler 계약](https://docs.python.org/3/library/http.server.html)을 사용했습니다. 이 서버는 로컬 합성 미리보기용이며 외부 서비스 배포용으로 만들지 않았습니다. 단말 전체에서 사용자의 직접 shell 실행이나 다른 앱을 금지하는 OS sandbox는 아닙니다.

## 검증 결과

| 검사 | 결과 | 근거 |
| --- | --- | --- |
| init.sh | PASS | [로그](preview-only-checks.log): Python 33개·Node 2개, compileall, lint, typecheck, 기존 Skill·도구 검사 |
| 실제 npm studio 진입점 | PASS | bash → studio.py → read-only preview_ready. Native Studio·Node renderer·agent process를 시작하는 코드 제거 |
| 합성 렌더 | PASS | synthetic-20261018-151755-5c1016f2, 6초·1280×720·H.264/AAC. [QA](../work/synthetic-20261018-151755-5c1016f2/verify.json) |
| HTTP 실측 | PASS | 23건: 화면·영상·HEAD·range, agent/편집/설치/렌더/전사 경로 404, 쓰기 405, 외부 Host/Origin 403, upgrade 400. [기록](preview-only-http.json) |
| 실제 브라우저 | PASS | 1280×720 viewport에서 무음 재생 완료 후 약 0.99초로 탐색, caption 확인. [기록](preview-only-browser.json), [화면](preview-only-viewer.png) |
| 상태·출력 보존 | PASS | HTTP 확인 및 render 재사용 후 파일 mtime 동일, 출력 hash 일치. 기존 props 미사용·미변경 |
| 실패 조건 | PASS | run 상태·lock·scope·hash·symlink·큰 snapshot·불량 range 거부. --refresh는 exit 2이며 변경 없음 |
| 시작·SIGTERM 종료 | PASS | 0.073초 시작, exit 0, port 해제, 최종 코드의 HTTP 23건·출력 보존 재검증. [기록](preview-only-lifecycle.json) |
| 마감 검사 | PASS | [변경 범위·링크·구문 검사](preview-only-closeout.json) |
| 원본 처리·음원 다운로드·ASR·게시 | NOT_RUN | 사용자 제한 유지 |
| 사람의 전체 시청·청취·취향 평가 | NOT_RUN | 합성 영상의 무음 playback과 기술 검사만 수행 |

합성 run ID의 날짜·시간은 UTC를 사용합니다. 검증은 한국 시간 10월 19일에 완료했습니다. 새 Claude model 호출은 하지 않았습니다. 기존 Claude launcher·Skill은 변경하지 않았고 무결성·PATH 검사는 init.sh에서 다시 통과했습니다.

## 발견한 문제와 처리

처음 작성한 테스트의 multiline with 문법 오류를 수정한 뒤 전체 검사를 통과했습니다. 첫 실제 서버 실행에서는 Python HTTPServer의 기본 hostname 역조회가 시작을 지연시킬 수 있는 경로를 확인했습니다. 숫자 loopback 주소는 조회가 필요 없으므로 해당 단계를 제거하고 DNS 호출이 없는 회귀 테스트를 추가했습니다. 변경 후 새 합성 run을 렌더해 실제 서버가 즉시 ready를 반환하고 재생되는 것을 확인했습니다.

종료 검사에서는 SIGTERM handler의 InterruptedError를 macOS selector가 흡수해 종료가 지연되는 문제도 재현했습니다. [실패 기록](preview-only-lifecycle-failed.json)을 남기고 selector 밖으로 전달되는 예외로 수정했습니다. 새 최종 run에서 실제 SIGTERM 종료와 port 해제를 확인했습니다.

브라우저 재생·탐색 화면은 종료 처리 수정 전 run인 synthetic-20261018-151327-d6ceff08의 증거입니다. 이후 변경은 종료 handler이며 화면·영상 코드는 같고, 최종 run의 영상 hash도 같습니다. 최종 코드의 HTTP·상태·종료 검사는 preview-only-lifecycle.json을 기준으로 합니다.

이전 run과 실패 기록은 보존했습니다. Native Studio props 갱신 테스트는 더 이상 지원하지 않는 기능이므로 읽기 전용 viewer의 동작·거부 테스트로 교체했습니다. 처음 검토한 기록은 `/private/tmp/vlog-preview-only-iiomw8k4`의 snapshot으로 보존했습니다.

## 상태와 제한

검증용 서버·탭은 종료했습니다. Git repository는 계속 미초기화 상태이며 commit·push·설치·전역 설정·credential 변경은 없습니다. 공식 Skill, project config, dependency lock과 기존 원본 설계도 유지했습니다. README·CLAUDE.md·workflow·progress·handoff·feature tracker는 현재 동작으로 갱신했습니다.

현재 범위는 합성 환경입니다. 실제 촬영본 ingestion·ASR·장면 선별·예능 자막·음원 선택·권리 검증·장시간 성능을 구현하거나 검증한 것으로 확대하지 않습니다. 미리보기 경로의 agent·편집 기능 문제는 해소했으며, 실제 제작을 자동으로 시작하지 않습니다.
