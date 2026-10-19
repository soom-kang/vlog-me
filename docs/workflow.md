# vlog-me 작업 절차

## 허용 범위

현재 단계는 `setup_synthetic_only`입니다. Claude Code 주 세션과 공식 Remotion Skill을 사용하며 Custom Skill·subagent·외부 coordinator는 없습니다. 설계의 전체 제작 pipeline이 구현된 상태는 아닙니다.

| 구간 | 구현 상태 |
| --- | --- |
| 도구 점검·Skill 무결성·지침·인수인계 | 구현 |
| 합성 asset 생성·inventory·timeline·기본 caption·믹스·렌더 QA | 구현 |
| 상태 저장·hash 검증·실패/partial 보존·재개 | 합성 run에 한해 구현 |
| production 범위 검증·`prod-*` run·`sources/` 경로·timeline v2 검증·원본 보호 hook | 구현(`scripts/production.py`); phase 전환 전이라 실행 진입점 없음 |
| 원본 ingest: inventory·hash·VFR/HDR/회전 감지·CFR 1080p SDR proxy·HEIC→JPG | 구현(`scripts/ingest.py`), 합성 fixture로만 검증. 실제 원본은 phase 전환 후 |

`python3 scripts/ingest.py run --source-root sources/<여행>`은 새 `prod-*` run을 만들고 원본을 읽기만 합니다. 처리하지 못한 파일은 이유와 함께 `sources.json`의 `skipped`에 남고, HDR proxy는 `color_review: needed`로 표시됩니다. 촬영 시각은 UTC로 정규화하며, 시간대 정보가 없는 사진은 이 Mac의 시간대로 해석합니다.
| 분석: 한국어 전사(whisper.cpp `ggml-large-v3-turbo`)·소리 이벤트·정적·장면 전환·contact sheet·클립 요약 | 구현(`scripts/analyze.py`), 합성 fixture로만 검증 |
| 후보 카드·기대 화면·선택 기록 | 구현(`scripts/review.py`, `renderer/src/production/`), 합성 fixture로만 검증 |
| 자막 preset 레지스트리·번들 폰트·글자 수/비율 검사 | 구현(`renderer/src/production/presets.json`, [자막 가이드](caption-style.md)) |
| 최종 timeline 조립 | 미구현(단위 6 이후) |

후보 리뷰 흐름은 다음과 같습니다.
1. Claude가 `analysis/index.md`와 클립 요약을 읽고 `work/<run>/candidates.json`을 씁니다. 후보마다 `id`(c01), `title`, `tag`(fun/mood), `source`, `range`(원본 초), `reason`, `evidence`, `dialogue`, `key_moment`(편집 후 초), `preview`(true/false), `plan`(`cuts`, `speed`, `zoom`, `captions`, `sfx`, `bgm`, `notes`, 사진은 `photo_seconds`)을 담습니다.
2. `python3 scripts/review.py build --run-id prod-...`가 새 `review/vN/`에 원본 프레임 4장, 자막을 합성한 기대 화면, 요청한 후보의 960×540 미리보기를 만듭니다. 이전 버전은 덮어쓰지 않습니다.
3. 사용자는 `open work/<run>/review/vN/index.html`로 페이지를 열고 채팅으로 `c01 채택`, `c03 자막 수정: …`, `c05 제외`처럼 답합니다.
4. Claude가 답을 `selection.json`(`decisions`: 후보마다 `adopt`·`caption_edit`·`drop`, 수정이면 `note`)으로 옮기고 `review.py select`로 기록합니다. 리뷰 뒤에 `candidates.json`이 바뀌면 선택을 거부하므로 다시 build합니다.

등록된 음원을 지정한 효과음·BGM은 미리보기 소리에 들어가고, BGM은 대사 구간에서 자동으로 12 dB 낮아집니다. 음원을 지정하지 않은 항목은 계획만 표시합니다. 자세한 기준은 [사운드 가이드](sound-guide.md)에 있습니다.

`python3 scripts/analyze.py --run-id prod-...`는 ingest가 끝난 run의 proxy만 읽습니다. Claude는 `analysis/index.md`와 클립별 `summary.md`부터 읽고, 필요한 구간만 contact sheet로 확인합니다. `reaction`은 대사 밖의 큰 소리라는 신호일 뿐 웃음이라는 판정이 아닙니다. Whisper는 음악·정적 구간에서 없는 대사(예: 자막 제작자 문구)를 지어낼 수 있습니다. 알려진 문구이거나 정적과 대부분 겹치는 대사는 `의심`으로 표시되고 웃음 후보 판정에서 빠집니다. 이 표시는 휴리스틱이므로 후보를 고를 때 화면과 함께 확인합니다. 실패하면 이전 시도를 `analysis.failed-*`로 남기고 다시 실행할 수 있습니다.
| 음원 등록·hash·loudness 측정·사용 판정(`audio_library.py`) | 구현. 등록된 실제 음원 0개 |
| 무료 음원 탐색·다운로드 | 절차만 문서화. production config의 `audio_search`·`audio_downloads`와 파일별 사용자 승인 필요 |
| 권리 사실 확인 | Claude가 공식 근거를 확인해 기록. 판정은 no-claim 보증이 아님 |
| 게시·Content ID 검사 | 미구현·권한 없음 |

## 시작과 상태

`./init.sh`로 로컬 상태를 확인합니다. root feature tracker는 구현 진행 상태이며 제작 run의 `state.json`과 역할이 다릅니다. root notes는 다음 작업과 근거 위치를 안내합니다.

`./scripts/smoke-render.sh`는 원본 경로를 받지 않고 FFmpeg `lavfi`로 source를 직접 생성합니다. asset hash를 manifest에 기록한 뒤 ffprobe로 inventory를 만들고 렌더합니다. setup 입력은 CFR 30fps H.264/AAC 영상, PNG 사진, PCM WAV 테스트 톤이며 출력은 1280×720 H.264/AAC입니다. 실제 납품 규격 확정이 아닙니다.

`brief.json`은 생성 당시 설정을 보존하고 `timeline.json`은 컷·caption·audio cue를 담습니다. 연속 컷의 합이 출력 길이입니다. 원음은 Video에서 mute하고 Audio cue로 한 번만 포함합니다. gain envelope는 cue 내부 frame과 dB로 표현합니다. 테스트 톤을 실제 무료 asset의 권리 상태로 등록하지 않습니다.

기존 run의 fingerprint는 저장된 brief를 사용합니다. 새 run용 기본값이나 사용하지 않는 음원 목록을 바꿔도 기존 결과를 무효화하지 않습니다. 반면 생성·렌더·미리보기 시작은 현재 setup 권한을 별도로 검사하며, 준비 완료와 최종 영상 확정 직전에도 권한을 확인합니다. run의 concurrency와 timeout은 brief에 보존한 값으로 실행합니다. 현재 지원 범위는 concurrency 1–2, timeout 1–180초입니다.

## 검사와 종료

1. 경로 traversal·symlink·hard link, source hash, cue ID·시간·source bounds를 검사합니다.
2. run lock을 획득하고 `running`을 기록합니다. Node renderer도 같은 validator와 호출한 Python의 lock 소유자를 확인합니다.
3. 단일 composition을 `preview.partial.mp4`로 렌더합니다. 기존 bundle/output은 덮어쓰지 않습니다.
4. stream·길이·decode·최종 loudness를 검사하고 입력이 바뀌지 않았는지 확인합니다. 테스트 true peak 상한 -1 dBTP는 플랫폼 납품 규칙이 아닙니다.
5. 검증 파일을 `preview.mp4`로 확정하고 QA·credit·출력 hash를 기록한 뒤에만 `succeeded`로 변경합니다.

`status`는 읽기 전용으로 hash를 대조하고 변경 시 `stale`을 보고합니다. 성공 run의 `render` 재호출은 결과를 재사용합니다. 실패·중단·stale·잔여 lock/partial은 원인과 파일을 보존하고 새 합성 run으로 검증합니다. production 부분 재렌더 지원으로 표현하지 않습니다.

준비를 시작할 때 run ID와 `fixture_generation/running` 상태를 먼저 기록합니다. FFmpeg뿐 아니라 inventory 생성까지 실패 원인을 저장하며, manifest가 없어도 해당 실패 상태를 조회할 수 있습니다. `state.json` 자체가 없거나 owner/run ID·stage/status가 맞지 않으면 추정 복구하지 않습니다. Ctrl-C와 CLI의 SIGTERM은 소유한 하위 process group을 종료한 뒤 `paused`를 남깁니다. SIGKILL·전원 중단은 정리할 수 없으므로 남은 `running`·lock을 직접 확인해야 합니다.

아직 렌더하지 않은 `prepared/pending` run은 timeline 수정 후 `render`를 호출하면 전체 입력을 다시 검사하고 fingerprint를 갱신합니다. 기존 output/bundle이 없어야 합니다. 완료·실패 run의 fingerprint를 덮어써 재사용하는 예외가 아닙니다.

## 실패 신호

- exit `0`: 해당 command 범위의 성공. `status`의 JSON 상태도 확인해야 합니다.
- exit `1`: 도구·계약·경로·상태 검사 또는 렌더 실패. 기록과 남은 artifact를 확인합니다.
- argparse exit `2`: 인자 형식 오류 또는 제거된 옵션(`--refresh`) 사용. 다른 방식으로 원본 접근 제한을 우회하지 않습니다.
- exit `130`: Ctrl-C로 중단. 보존한 state를 확인합니다. CLI SIGTERM은 exit `1`과 `paused` state를 남깁니다.
- `not_checked` / `NOT_RUN`: 플랫폼·사람 청취·ASR 등의 미검증. 기술 검사로 자동 승격하지 않습니다.

## 이후 실제 제작

원본 처리 범위가 허용된 뒤 유형·이야기·톤·source root·제공할 자료 범위·budget을 brief에 정하고 production ingestion과 ASR을 구현·검증합니다. 합성 manifest에 원본을 복사해 넣어 우회하지 않습니다.

## 미리보기 전용 실행

`./scripts/studio.sh RUN-ID`는 기존 명령 이름만 유지한 읽기 전용 뷰어입니다. npm의 studio 명령도 같은 helper로 연결됩니다. native Remotion Studio·agent·편집 backend를 시작하지 않고 Python 표준 라이브러리로 `127.0.0.1`의 임시 port를 엽니다. 기존 Remotion Skill 원문은 유지하되 upstream Studio 실행 예제 대신 이 helper를 사용합니다.

시작할 때 현재 scope, run lock, succeeded 상태, 입력·출력 hash를 확인합니다. 검증된 preview.mp4를 최대 128 MiB의 메모리 snapshot으로 읽으며 HTTP 요청에서는 파일을 열지 않습니다. 이 한도는 합성 환경의 메모리 범위이고 본편 길이 정책이 아닙니다. pending·failed·paused·stale·변조·잠금 상태에서는 서버를 시작하지 않습니다.

허용 경로는 `/`와 `/preview.mp4`, 허용 동작은 GET·HEAD뿐입니다. 영상의 byte range 요청은 탐색을 위해 지원합니다. agent·편집·설치·render·전사·WebSocket·디렉터리 탐색 경로는 없으며 쓰기 요청을 거부합니다. 페이지는 JavaScript 없이 native video controls만 사용합니다. 외부 Host·Origin과 protocol upgrade도 거부합니다. 외부 서비스 배포용 서버는 아닙니다.

viewer는 state·props·출력을 수정하지 않습니다. 이미 연 화면은 시작 당시 저장본이므로 canonical timeline 변경을 실시간 반영하지 않습니다. 새 pending 합성 run을 Claude Code에서 수정하고 렌더한 뒤 새 완료 run을 엽니다. 이전 --refresh는 안내 메시지와 함께 exit 2로 종료하며 과거 props·owner 파일을 삭제하거나 채택하지 않습니다. 확인 후 Ctrl-C로 서버를 종료합니다.

현재 사실은 [미리보기 전환 보고서](../reports/preview-only-review.md), [이전 적대적 검토](../reports/adversarial-review.md), config/toolchain.json을 우선합니다. 기존 설계는 목표 구조를 설명하며 미구현 기능의 실행 지시가 아닙니다.
