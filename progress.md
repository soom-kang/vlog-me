# Session Progress

## Current State

- Last Updated: 2026-10-19 Asia/Seoul
- Active Feature: first-real-sample. `sources/vietnam-20260527/`로 첫 실제 sample을 진행 중이며 최종 렌더 완료(`render/v3/final.mp4`, 56.9초, QA PASS). 노을 BGM은 Mixkit Serene View로 교체(다운로드 1건, 사용자 위임). 사용자 시청 대기. 근거: reports/first-sample-review-2026-10-19.md
- 단위 1–8은 완료(합성 fixture 검증)
- 2026-10-20 harness 수정: `./init.sh`가 production에서도 PASS(124개). doctor가 phase·전사 모델·등록 음원을 실제로 보고하고, 테스트는 live 설정 대신 `config/setup.example.json`과 임시 폴더를 씁니다. 합성 렌더(`smoke-render.sh`)는 setup phase 전용입니다.
- Scope: production (source_roots: sources/vietnam-20260527). audio_search·audio_downloads·production_render false. 합성 run·합성 scope 테스트는 setup 설정으로 되돌린 뒤 실행
- 이번 변경: scripts/analyze.py contact sheet `eof_action=pass`(1초 미만 클립 분석 실패 수정), scripts/render_prod.py loudnorm 뒤 alimiter(조용한 현장음에서 true peak QA 실패 수정), 후보 `inserts`(사진 오버레이)·`mute`(원음 구간 음소거) 기능과 tests/test_inserts.py
- Repository: Git 저장소(main). commit·push는 명시 요청 시에만

## Completed

- 기존 공식 Remotion Skill 143개 파일·ref·hash 유지.
- Claude 시작 환경, scope 재검사, 실패 기록·중단 정리·출력 보존 유지.
- native Studio 실행 제거. studio.sh 및 npm studio는 읽기 전용 encoded preview만 제공.
- loopback bind, GET/HEAD 두 경로, byte range, 쓰기·agent·편집·설치·render API 거부.
- Python 112개(production 계약부터 조립·롱폼 렌더까지 포함, 미디어 smoke 6개는 skip)·Node 2개·lint·typecheck 통과(2026-10-19). 새 합성 smoke render succeeded.
- 실제 HTTP 23건·브라우저 재생과 탐색·파일 mtime 보존 통과.
- SIGTERM 종료 회귀 수정, exit 0과 port 해제 실측 통과.
- 최종 run: synthetic-20261019-064243-1f9751cd. 날짜는 UTC.

## Evidence

- reports/preview-only-review.md: 현재 동작·변경·검증·제한.
- reports/preview-only-checks.log: 최종 정적·계약 검사.
- reports/preview-only-lifecycle.json: 최종 코드의 시작·HTTP·재사용·mtime·SIGTERM 종료.
- reports/preview-only-http.json: 앞선 HTTP 확인.
- reports/preview-only-browser.json 및 preview-only-viewer.png: 재생·탐색 화면.
- reports/adversarial-review.md 및 setup-report.md: 이전 검토의 역사적 근거.
- reports/claude-review-check.json: 이전 세션의 실제 Claude Skill 호출. 이번에는 model 재호출 없음.

## Decisions and Limits

- Custom Skill·subagent·automation·dependency 추가 없음.
- 유형·톤은 제작 prompt에서 결정하고 목표 길이는 null.
- live --refresh 제거(안내 메시지와 exit 2). 새 run을 Claude Code에서 수정·렌더한 후 완료 영상을 미리보기.
- 뷰어는 128 MiB 이하의 검증된 합성 snapshot만 재생하며 state·props·영상을 변경하지 않음.
- 검증용 서버·탭 종료. 실패·partial·lock·stale은 보존.

## Deferred

관찰: 2026-10-19 합성 렌더 1회(synthetic-20261019-051010-fabe9121)가 139프레임 delayRender timeout으로 실패해 보존했습니다. 이후 폰트 로딩을 자막 첫 렌더 시점으로 옮겼고, 연속 5회 렌더는 성공했습니다. 원인은 확정하지 못했습니다.

다음 후보: 첫 실제 sample([로드맵](docs/roadmap.md) "다음: 첫 실제 sample", `/vlog-workflow`로 시작, phase 전환 요청 필요). 2분 합성 롱폼: 3720프레임·5구간·-14.96 LUFS·TP -1.43·A/V 최대 17ms, 렌더 434초(약 3.5배). 등록된 실제 음원은 0개이며, 다운로드는 파일별 승인이 필요합니다. OFL 폰트 5종은 2026-10-19 승인·Git 포함(config/fonts-lock.json). 자막 갤러리: reports/unit5-caption-gallery.jpg. 단위 4 기대 화면 예: reports/unit4-expected-frame-synthetic.jpg. Whisper 모델 ggml-large-v3-turbo는 2026-10-19 승인·설치(.tools/whisper, SHA-256 확인). 사용자 요청 시에만 시작. 설계: docs/superpowers/specs/2026-10-19-production-harness-design.md.

원본 처리·ASR·음원 다운로드·권리 확인·취향·사람 청취·장시간/4K·업로드는 NOT_RUN입니다.
