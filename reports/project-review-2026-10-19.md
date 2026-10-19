# vlog-me 적대적 리뷰 (2026-10-19)

## Context

목표는 실제 여행 영상·사진에서 재밌는 포인트와 감성 장면만 골라 예능 자막을 입힌 유튜브 롱폼 브이로그(재미 60 · 감성 40)를 Claude Code 하나로 편집하는 것입니다. 1차 환경 구성이 끝난 지금, sharpen 계열 Skill로 이 목표를 기준 삼아 harness를 적대적으로 점검했습니다.

- 관찰일: 2026-10-19
- 범위: 읽기 전용. `./init.sh`와 렌더는 실행하지 않음(NOT_RUN)
- 실행한 검사: 최신 run `synthetic-20261018-151755-5c1016f2`의 `status` 조회 → `succeeded`

## 1. 현재 상태 (sharpen-brief)

**결론: 안전장치와 합성 렌더 검증은 탄탄합니다. 하지만 목표에 필요한 편집 기능은 아직 하나도 없습니다.**

검증된 것:
- 합성 영상·사진·테스트 톤으로 단일 timeline 렌더, decode·길이·loudness QA
- run lock, hash 기반 stale 판정, 실패·partial 보존, SIGTERM 정리
- 읽기 전용 preview 뷰어(loopback)
- 공식 `remotion-best-practices` Skill의 hash 고정

없는 것 (모두 `not-started`):
- 원본 ingestion(VFR·HDR·HEIC·HEVC 처리)
- 한국어 ASR, 장면·웃음 포인트 탐색
- 스토리 선별, 예능 자막 스타일
- BGM·효과음 확보와 배치

미해결 결정: 원본 처리 단계(`real-media-validation`)를 언제, 어떤 범위로 열지가 정해지지 않았습니다.

## 2. 목표 대비 가정 검증 (sharpen-challenge)

목표를 무너뜨릴 수 있는 가정을 영향이 큰 순서로 정리했습니다.

### A1. 범위를 넓힐 경로가 없음 — 코드로 확정, 차단
- `scripts/common.py`의 `validate_setup_config`는 `phase == setup_synthetic_only`가 아니면 모든 쓰기 진입점을 거부합니다.
- 다음 phase(예: `real_media_sample`)의 config 모양, 허용 경로, 해제 절차가 정의되어 있지 않습니다.
- 그래서 사용자가 원본 처리를 허락해도 harness는 그대로 쓸 수 없습니다.

### A2. 합성 파이프라인이 실제 편집으로 일반화되지 않음 — 코드로 확정
- `check_assets`: asset 집합이 `{video, photo, bgm, sfx}` 4개로 고정
- `validate_timeline`: 1280×720·30fps 고정, 원본 영상 1개 전제, caption `kind`는 `editorial`만 허용
- `renderer/src/Timeline.tsx`: 자막 스타일 하나, 시스템 폰트(Apple SD Gothic Neo), "SYNTHETIC SETUP" 워터마크가 유일한 composition에 박혀 있음
- `create`의 테스트 길이 2–30초, 렌더 timeout 상한 180초 → 롱폼 렌더 불가
- 결론: 합성 PASS는 실제 편집 경로의 근거가 되지 못합니다. timeline v2 계약과 production composition을 새로 만들어야 합니다.

### A3. Claude가 "재밌는 포인트"를 찾을 수 있다 — 미검증, 가장 큰 불확실성
- Claude는 영상을 frame 이미지와 전사로만 봅니다. 예능의 웃음은 대사·타이밍·리액션(소리)에 몰려 있어 ASR 없이는 탐지가 어렵습니다.
- 현재 ASR 없음, frame 샘플링·contact sheet 도구 없음, 오디오 피크·웃음소리 후보 추출 없음.
- **가장 작은 검증:** 허가받은 2–3분 클립 1개 → 1fps contact sheet + 로컬 Whisper 전사 + 음량 피크 목록을 만들고, Claude가 고른 재미·감성 구간을 사용자가 직접 표시한 구간과 비교합니다.
  - 사용자 표시 구간을 대부분 맞히면 자동 후보 + 사용자 확정 방식으로 진행합니다.
  - 대부분 놓치면 사용자 타임스탬프 메모를 1차 입력으로 삼는 방식으로 설계를 바꿉니다.

### A4. 4K·HEVC·HDR·VFR 원본을 Remotion으로 롱폼 렌더할 수 있다 — 미검증
- Chrome for Testing의 HEVC·HDR decode와 VFR 프레임 매핑이 확인되지 않았습니다.
- **가장 작은 검증:** 아이폰 원본 60초 1개를 FFmpeg로 CFR H.264 1080p SDR proxy로 변환한 뒤 렌더하고, 실시간 대비 렌더 배율과 싱크를 측정합니다.

### A5. 예능 느낌의 핵심인 효과음·BGM을 쓸 수 있다 — 현재 0개
- `audio_downloads: false`, `media-licenses.json`의 assets가 비어 있음
- 세 플랫폼 동시 검증 조건(`audio_eligibility`)은 엄격해서 후보가 0개일 수 있습니다.
- 현실적인 경로: 사용자가 직접 받은 소수의 음원(예: YouTube Audio Library)을 권리 근거와 함께 등록합니다. 1차 목표는 YouTube로 한정합니다.

### A6. 롱폼 원본 전체가 context에 들어간다 — 설계만 있음
- 설계 7절에 구간별 저장·재개 방식이 있지만 `moments.json` 같은 저장 계약은 구현되지 않았습니다.

## 3. 문서 cold read 결과 (sharpen-cold-review)

별도 context의 Explore 에이전트가 7개 문서만 읽었습니다. 판정은 **gaps_present**입니다.

1. 범위를 푸는 방법이 문서에 없습니다. "별도 요청으로 정합니다"뿐이고 예시 프롬프트도 없습니다.
2. 목표까지의 로드맵이 없습니다. 미구현 사실이 workflow·README·progress에 흩어져 있습니다.
3. 60:40을 "시간 quota로 쓰지 않는다"고만 하고, 무엇으로 반영하는지는 설명하지 않습니다.
4. 시작 순서가 문서끼리 다릅니다. handoff는 `init.sh` 선실행, getting-started는 불필요하다고 씁니다.
5. 첫 점검에서 stale이 나오면 정상인지 FAIL인지 getting-started에 없습니다.
6. `--refresh` 종료 방식이 4곳에서 다르게 적혀 있고, exit 2는 "인자 형식 오류" 정의와 섞입니다.
7. CLAUDE.md·progress·README는 "Git 미초기화"라고 쓰지만 실제로는 Git 저장소입니다(`ed0c206`).
8. CLAUDE.md가 매 세션 로드되기에는 깁니다. 뷰어 설명이 5곳에 중복되고 design 경로가 빠져 있습니다.
9. fingerprint, stale, gain envelope, dBTP 등 용어 설명이 없습니다.

## 4. Harness 자체의 추가 지적

- `.claude/settings.json`은 `Read(raw/**)`만 막습니다. `Bash(cat raw/...)`나 ffmpeg 입력은 막지 않습니다. 설계가 제안한 `PreToolUse` hook도 없습니다.
- allow 목록이 없어 `init.sh`, `synthetic.py status` 같은 안전한 명령도 매번 권한을 묻습니다.
- `reports/`에 파일 25개(과거 로그 포함)가 있어 최신 근거를 찾기 어렵습니다.
- `input_fingerprint`가 `scripts/*.py` 전체를 포함합니다. 무관한 helper를 고쳐도 모든 run이 stale이 됩니다. 의도된 설계이지만 production에서는 재렌더 비용이 커집니다.
- 노력의 배분: 뷰어·lock·복구 보증에 비해 편집 능력(선별·자막·사운드)에 대한 구현과 검증이 0입니다.

## 5. 개선 계획 (권장 순서)

각 단계는 한 번에 하나의 feature로 진행하고, 단계마다 사용자 승인을 받습니다.

### 단계 0 — 문서·harness 정리 (behavior-preserving, sharpen-refine 범위)
- `CLAUDE.md`: Git 상태 수정, design 경로 추가, 뷰어·복구 세부는 `docs/workflow.md` 링크로 축약
- `progress.md`·`README.md`·`session-handoff.md`: Git 표기 수정, 시작 순서 통일(`claude.sh` → Claude가 `init.sh` 실행)
- `--refresh` 종료 설명을 실제 동작(exit 2) 하나로 통일
- `docs/getting-started.md`: stale 판정 기준 한 줄 추가
- 새 `docs/roadmap.md`: 목표까지의 단계와 각 단계를 여는 예시 프롬프트
- `.claude/settings.json`: 읽기 전용 명령 allow 추가, `Bash(* raw/*)`·`Bash(* sources/*)` deny 추가
- `reports/`: 과거 로그를 `reports/archive/`로 이동(삭제하지 않음)

### 단계 1 — 범위 전환 계약 정의
- `config/project.json`에 `real_media_sample` phase 정의: `source_roots` 1개, 클립 수 상한, 외부 전송 금지 유지
- `scripts/common.py`: phase별 검증 함수로 분리하고 synthetic 경로는 그대로 유지
- 테스트: synthetic 회귀 전체 + 새 phase 허용·거부 케이스

### 단계 2 — 원본 sample 검증 (A3·A4 실험)
- ingestion helper: ffprobe inventory, CFR 1080p SDR proxy 생성(원본 무변경)
- 분석 helper: frame contact sheet, 음량 피크·무음 구간 목록
- 로컬 ASR 1개 선택·설치(예: whisper.cpp, 한국어 모델) — 다운로드는 별도 승인
- 결과: `moments.json` 계약 + Claude 후보 vs 사용자 표시 비교 보고

### 단계 3 — 예능 자막·composition
- timeline v2: 다중 클립, `dialogue`/`editorial`/`sfx_text` 자막 kind, 스타일 preset
- 예능 자막 컴포넌트 3–5종(강조 팝업, 화자 색, 효과 텍스트, 감성 구간 잔잔한 자막), 라이선스 확인한 한글 폰트 번들
- 이 시점에 `k-variety-caption-director` Custom Skill 필요성 재평가

### 단계 4 — 사운드·롱폼 렌더
- 사용자가 제공한 음원 등록 절차(YouTube 우선), BGM ducking·효과음 배치
- 롱폼 렌더 timeout·분할 렌더, 사람 시청 검수

## Verification

- 단계 0: `./init.sh` PASS, `python3 scripts/synthetic.py status --run-id synthetic-20261018-151755-5c1016f2`, 문서 cold read 재실행으로 9개 지적 해소 확인
- 단계 1: 기존 Python 33개·Node 2개 테스트 + 새 phase 테스트, `./scripts/smoke-render.sh`
- 단계 2 이후: 각 단계의 sample run 보고서에 PASS / FAIL / NOT_RUN / BLOCKED 분리 기록

## 단계 0 실행 결과

- PASS: `./init.sh` (Python 33개·Node 2개·lint·typecheck)
- PASS: 최신 합성 run status `succeeded` (문서·설정 변경은 fingerprint 대상이 아님)
- 변경: reports 파일 이동 대신 `reports/README.md` 색인 추가. 대부분의 파일이 다른 보고서에서 경로로 참조되어 이동하면 링크가 깨지기 때문입니다.
- NOT_RUN: 합성 렌더, settings deny 패턴의 실제 차단 동작 확인
- 단계 1 이후는 별도 요청으로 시작합니다.
