# Session Progress

## Current State

- Last Updated: 2026-10-22 Asia/Seoul
- 2026-10-23 하우스 스타일 저장: 사용자가 render v3 세팅을 확정했습니다. 앞으로의 영상은 docs/house-style.md를 기본으로 감성 95 · 예능 5로 진행합니다. presets.json(목표 0.95, 범위 0.85–1.0, 레퍼런스형 preset이 기본값), config 문구, CLAUDE.md·README·roadmap·가이드, Skill 3개와 lock을 갱신했습니다. init.sh PASS(182, 7 skip).
- 2026-10-23 본편 render v3 완료: `work/prod-20261020-053818-932c04b5/render/v3/final.mp4`(9분 18.9초, QA 8/8 PASS, -14.1 LUFS, -1.75 dBTP). 화면을 보고 말하는 장면(c38·c45·c74)은 BGM 없이 원음(현장음 포함)만 두어 pause마다 볼륨이 오르내리지 않게 했고, 쿠키(c76)는 BGM을 목소리 아래에 유지했습니다. 76개 전부 채택(리뷰 v16), 조립 시 디졸브 3곳은 컷으로 자동 보정. production_render는 다시 false. v1·v2는 보존. 사람 시청 NOT_RUN.
- 2026-10-23 리뷰 v15: 사용자가 승인한 Mixkit 4곡(Forest Mist Whispers, Chillax, Slow Pop, Old Letter)을 받아 등록했습니다(assets/audio/library/mixkit-148·655·351·854, media-licenses.json). audio_downloads는 다시 false입니다. 장별 BGM은 아침 Slow Pop, 리조트·점심 Chillax, 객실·오후 바다 Forest Mist, 노을 Sunset Dream, 밤·저녁 Old Letter, 야시장·엔딩 Serene View, 쿠키 Clumsy Daddy입니다. 곡별 음량 차이를 gain으로 맞췄습니다(약 -27 LUFS 기준). 청취는 NOT_RUN입니다. 이전 후보는 candidates.prev-20261022-v14.json.
- 2026-10-22 리뷰 v14: 목소리는 그녀가 화면을 보고 혼자 말하는 4개(c38·c45·c74·c76)만 살리고, 나머지 대사 후보 9개는 원음을 끄고 감성 자막(talk-note)으로 바꿨습니다. BGM은 차분한 2곡(Serene View·Sunset Dream)만 쓰고 쿠키만 Clumsy Daddy입니다. 감성 82%. 사용자 동의로 audio_search=true(다운로드는 false). Mixkit 감성곡 10개 후보를 제안했고 받지는 않았습니다. 이전 후보는 candidates.prev-20261022-v13.json.
- 2026-10-22 리뷰 v13(제작): 후보 76개(약 9분 19초)의 자막을 레퍼런스형 구어체로 다시 썼고, 대화가 겹치는 장면 4개(점심 v066, 밤 바 v115·v119, 저녁 v139)를 원음 없이 BGM과 요약 자막으로 추가했습니다(0.5초 프레임 확인, 동행 암시 단어 0건). BGM은 레퍼런스 음량 범위(오눅 LRA 20–26 LU, 걍민경 약 11 LU)를 참고해 -12~-14 dB로 낮췄고, 만화풍 효과음은 뺐습니다. 이전 후보는 candidates.prev-20261022-v12.json. 선택·조립·렌더 NOT_RUN.
- 2026-10-22 레퍼런스형 자막 preset(개발): 사용자가 넣어 둔 refers/*.mp4(오눅·걍민경, Git 제외)를 프레임으로 관찰해 구어체 고딕 자막 preset 5종(talk, talk-note, talk-mood, place-tiny, pop-word)을 추가했습니다. 대화 겹침 장면은 원음을 끄고 BGM만 깔며 혼자 말하듯 요약 자막을 다는 규칙을 문서화했습니다. init.sh PASS(182, 7 skip), 갤러리 reports/caption-gallery-v3.jpg. 2단계(후보 72개 문구 전면 수정, 대화 겹침 장면 추가, 리뷰 v13)는 갤러리 확인 뒤 진행합니다.
- 2026-10-22 감성 재선별: 사용자 요청으로 원본 전체(영상 150·사진 298)에서 감성 90 · 예능 10 후보를 다시 골라 리뷰 v12를 만들었습니다(후보 72개, 약 8분 22초, 풍경 b-roll·내레이션 14개·예능 후보 11개, 자막 비율 감성 79%). 남자 출연자(LA 모자·흰 상의, 노을 바 사진 p271–p290 등)는 제외, 새 대사 후보는 남성 음역 0건인 클립만. 이전 후보·선택은 *.prev-20261022-main-v1.json으로 보존. v11 리뷰는 렌더 중 브라우저 연결 끊김으로 실패해 보존. 선택·조립·샘플 렌더 NOT_RUN.
- 2026-10-22 render v2 완료: `work/prod-20261020-053818-932c04b5/render/v2/final.mp4`(4분 41초, QA 8/8 PASS, -14.47 LUFS, -1.96 dBTP). v1 보존. `production_render`는 다시 false. 프레임 확인 결과 c41 내레이션(흰 모래 위)과 c15 dialogue-soft(밝은 나무 위)는 대비가 약합니다. 사람 시청 NOT_RUN.
- 2026-10-22 본편 감성 스타일 적용(timeline만): run prod-20261020-053818-932c04b5의 timeline.json을 직접 고쳤습니다. 자막 109→67(내레이션 4: c21·c23·c33·c41, 대사 22는 문장·시각 그대로), look warm 0.5·grain 0.08·vignette 0.2, light_leak 2, 디졸브 c21(c18·c36·c43은 원본 프레임 부족으로 컷 유지), drift 4, 효과 9→3, 효과음 48→21. clip·순서·원음·BGM·overlay는 그대로. `render_prod.py --check` PASS(280.93초, 감성 62%). 백업 timeline.prev-20261022-render-v1.json. 렌더 v2는 NOT_RUN(요청·`production_render` 동의 필요). candidates.json은 갱신하지 않아 재조립하면 이 수정이 사라집니다.
- 2026-10-22 갤러리 still 2장 생성: reports/caption-gallery-v2.jpg, reports/look-gallery.jpg(gallery.mjs, 원본·timeline·config 변경 없음). 사용자 피드백 대기, 다음 단계는 자동으로 시작하지 않습니다.
- 2026-10-22 mood-vlog-style 완료(병합 95259e0): 자막 비율을 감성 90 · 예능 10으로 바꿨습니다. 내레이션 kind(4줄×22자, 줄이 차례로 등장), 감성 preset 10개(합계 43개), 화면 톤 look(warm/faded/film·grain·vignette·letterbox), light_leak·dissolve·drift를 추가했습니다. Skill 이름은 k-mood-caption이고, live config는 스타일 두 값만 바꿨습니다. dev-check PASS(180, 7 skip), init.sh PASS. 렌더·갤러리 still은 NOT_RUN입니다. 근거 reports/mood-vlog-style.md. 활성 feature 없음.
- 2026-10-22 (완료) orca-dev-orchestration. 개발 작업 전용 Orca 흐름(Claude coordinator·plan, Codex coding, 조건부 독립 리뷰, 한도 초과 시 Codex fallback)을 Claude 단일 세션에서 구현 중. 설계 docs/superpowers/specs/2026-10-22-orca-multi-agent-design.md, 계획 docs/superpowers/plans/2026-10-22-orca-multi-agent.md. first-real-sample은 그동안 보류(on_hold). 구현 완료: AGENTS.md, docs/orca.md, docs/orca/ 템플릿 4개, orca.yaml, scripts/dev-check.sh, tests/test_orca_harness.py. ./init.sh PASS(158), 원본 없는 임시 worktree에서 dev-check PASS(157). Orca repo 등록과 실패 receipt 확인(가짜 모델 ID → dispatch_input/providerRejected, 정리 완료)은 PASS. 실제 개발 Run·한도 초과 fallback은 NOT_RUN. 근거 reports/orca-dev-orchestration.md.
- (보류) first-real-sample. `sources/vietnam-20260527/`로 첫 실제 sample을 진행 중이며 최종 렌더 완료(`render/v3/final.mp4`, 56.9초, QA PASS). 노을 BGM은 Mixkit Serene View로 교체(다운로드 1건, 사용자 위임). 사용자 시청 대기. 근거: reports/first-sample-review-2026-10-19.md
- 2026-10-21 본편 렌더 완료: `work/prod-20261020-053818-932c04b5/render/v1/final.mp4`(4분 41초, QA 8/8 PASS, -14.5 LUFS, true peak -1.84 dBTP). 처음 렌더는 true peak -0.57 dBTP로 QA FAIL이었습니다. 리미터를 4배 오버샘플링으로 바꿔 다시 마무리했습니다. 깜빡임 보정(deflicker)과 사진 블러 배경 미리 굽기를 추가했습니다. 사람 시청 확인은 아직입니다.
- 2026-10-21 본편 선택 확정: 사용자가 v8의 대사 사이 편집이 흐름을 끊는다고 해서 v7 후보로 되돌렸습니다. v7 피드백을 반영해 리뷰 v9와 `review/sample-v9.mp4`(4분 42초)를 만들고 선택을 기록했습니다(채택 42, 삭제 8, 스토리 순서). 고친 것: 세로 영상 블러 배경 깜빡임(시간 평균), 사진 쌓기 흰 플래시 제거, c15·c22·c25 대사 끝까지, c49는 망고에서 끝, BGM은 곡마다 이어서 재생. 다음은 사용자가 요청하면 조립과 렌더입니다.
- 2026-10-20 본편 v2 피드백 3차: 남자 목소리는 그녀의 말과 겹치지 않으면 뮤트 대신 편집으로 잘라냅니다(c07·c48). 흔들림·흐림 측정으로 c04·c09·c15·c17·c37·c41을 다듬었습니다. 자동 흔들림 보정은 ffmpeg deshake와 자체 보정을 모두 시험했는데 효과가 없어 넣지 않았습니다. 결과물은 리뷰 v8과 `review/sample-v8.mp4`(5분 40초)입니다.
- 2026-10-20 본편 v2 피드백 2차: BGM이 빠지던 버그를 고쳤습니다(`sound.duck_envelope`가 전사 문장이 후보 전체를 덮으면 음악을 무음으로 만들던 문제). 원음은 실제로 말한 구간에서만 열리게 바꿨고, 저음 비율이 높은 7개 후보는 원음을 끄고 상황 자막으로 바꿨습니다. `bgm.offset`으로 장 안에서는 곡이 이어지게 했습니다. c21은 걷는 장면부터 시작합니다. 결과물은 리뷰 v7과 `review/sample-v7.mp4`(5분 59초)입니다.
- 2026-10-20 본편 v2 피드백 반영: 남자 목소리 통제를 harness 기능으로 넣었습니다. 대사 후보는 대사 자막 구간에서만 원음이 들리고(`"original": "dialogue_only"`), 나머지는 원음을 끄고 BGM으로 채웁니다. `scripts/voices.py`로 남은 남성 음역을 리뷰 카드에 경고합니다. 자막 겹침 자동 조정, 읽기 시간 보장, 작은 목소리 문장 끝 싱크도 고쳤습니다. 스토리는 시간순으로 다시 정렬했습니다(예외: 콜드 오픈, 인피니티 풀 장 시작). 숙소 장면은 엔딩 카드 뒤 쿠키 영상으로 뒀습니다. 결과물은 리뷰 v5와 `review/sample-v5.mp4`(6분 2초)입니다.
- 2026-10-20 본편 v2: `sources/vietnam-20260527/additional/`에 영상 120개(약 47분)가 추가되어 새 run `prod-20261020-053818-932c04b5`로 전체를 다시 ingest·분석했습니다(영상 150, 사진 298, 건너뜀 0). 하루 전체(07:32 공항 → 21:14 숙소)를 잇는 후보 50개, 약 6분 13초로 리뷰 v3를 만들었습니다. 기존에 확정한 17개는 그대로 포함했습니다. 남자 출연자·동행 암시는 0.5초 간격 프레임 확인과 음높이(전사 구간별 F0)로 걸렀습니다. 추천 길이는 5분 30초–6분 30초입니다. 사용자 선택 대기 중이고, 조립·렌더는 요청할 때만 합니다.
- 2026-10-20 본편: 같은 run에서 후보 17개(약 87초)로 리뷰 생성. 원본 10.7분 중 남자 출연자·동행 암시를 빼면 쓸 수 있는 영상이 약 2분이라 추천 길이는 1분 20초–1분 40초. 사용자가 17개 전부 채택(c03 자막 "약 2억 장", 세로 사진·영상의 검은 여백을 블러 배경으로). 세로 영상은 ffmpeg로 블러 배경을 구운 proxy(`proxy/fill/`)를 씁니다. 리뷰 v18, selected/pending. 조립·렌더는 요청 대기
- 단위 1–8은 완료(합성 fixture 검증)
- 2026-10-20 첫 sample 피드백 반영 중: 대사 자막 단어 단위 자동 타이밍, 자막 preset 33종(상단 박스 9종, 감성 6종)과 반복 경고, 효과(punch_zoom·shake·flash·speedlines), 사진 쌓기, BGM 비교 미리보기. 폰트 2종(Nanum Pen Script, Cormorant Garamond)·Mixkit 효과음 15개·BGM 3곡을 승인 후 등록. 목소리 구간 기반 자막 타이밍도 추가했습니다. 사용자가 리뷰 v14에서 BGM(낮 Owies Ukulele, 엔딩 Clumsy Daddy)을 골라 `render/v4/final.mp4`(56.9초, QA PASS)를 만들었고, 사용자가 2026-10-20 승인했습니다("lgtm"). 다음은 여행 전체 본편입니다.
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
