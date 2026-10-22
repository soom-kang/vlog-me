# vlog-me production harness 설계

> 2026-10-22: 자막 비율은 감성 90 · 예능 10으로 바뀌었습니다. [계획](../plans/2026-10-22-mood-vlog-style.md)

작성일: 2026-10-19 · 상태: 승인됨. 구현은 단위 1부터 하나씩 진행합니다. 현재 구현 상태는 `feature_list.json`과 `docs/roadmap.md`를 우선합니다.


## Context

1차 리뷰(reports/project-review-2026-10-19.md, commit b64987c)의 결론은 이렇습니다. 안전장치와 합성 렌더 검증은 탄탄하지만, 실제 제작 기능은 하나도 없습니다. 범위 검사(`validate_setup_config`)가 synthetic 외 phase를 모두 거부하고, asset 4종·1280×720·자막 1스타일로 고정되어 있습니다.

이번 목표는 실제 제작입니다.
- 입력: 길이가 제각각인 mp4 영상 여러 개, 아이폰 사진
- 결과: YouTube 롱폼 여행 브이로그. 내용은 재미 60 · 감성 40, 소소한 재미가 중심
- 자막: 예능 80 · 감성 20

사용자가 정한 것:
1. **장면 선별:** Claude가 후보를 내고 사용자가 확정합니다. 후보마다 구간, 선정 이유, 원본과 편집 후를 어떻게 바꿀지 설명합니다. **가장 중요한 건 기대 화면을 미리 보는 것**입니다.
2. **전사:** 로컬 Whisper를 씁니다. 확인해 보니 `whisper-cli`(whisper.cpp)가 이미 `/opt/homebrew/bin`에 설치되어 있어 모델만 있으면 됩니다.
3. **음원:** 두 가지를 함께 씁니다. 사용자가 직접 넣은 파일, 그리고 Claude가 무료 음원(효과음 포함)을 찾아 구간에 맞게 고른 것.

확인한 환경: Apple M4 Max, RAM 36GB, 여유 디스크 138GB. FFmpeg에 `scdet`·`ebur128`·`silencedetect`·VideoToolbox가 있지만 `zscale`은 없습니다. 그래서 HDR 톤매핑은 별도 경로가 필요합니다. `sips`(HEIC 변환)와 `@remotion/captions`도 사용할 수 있습니다.

## 결정 사항

사용자가 정한 것:
- 원본 위치: 프로젝트 안 `sources/<여행이름>/`. `.gitignore`로 Git에서 제외되어 있습니다.

Claude가 정한 것(검토 시 확인해 주세요):
- **run ID:** production run은 `prod-*` 접두사와 별도 진입점을 씁니다. synthetic helper는 계속 `synthetic-*`만 받으므로 `test_real_run_rejected_before_read`를 그대로 유지합니다.
- **sources/ 권한:** production phase에서 `Read(sources/**)`와 `Bash(* sources/*)` deny를 풀고, 대신 `Edit/Write(sources/**)` deny와 `rm`·`mv`·`cp`·`ffmpeg -y` 같은 쓰기 명령 deny를 둡니다. 추가로 `PreToolUse` hook이 `sources/`를 출력 대상으로 쓰는 명령을 차단합니다. 이 phase가 아닐 때는 지금의 전면 deny를 유지합니다.
- **리뷰 카드:**
  - 후보마다 기대 화면 still 1장을 핵심 순간 기준으로 만듭니다. 요청하면 컷마다 추가합니다.
  - 원본 프레임 4장은 시작, 피크 직전, 피크, 끝에서 고릅니다.
  - 카드는 원본 클립별로 묶어서 전부 보여줍니다.
  - 480p 미리보기 클립은 상위 후보와 요청한 후보만 만듭니다.
- **화자:** 별도 화자 분리 도구 없이 Claude가 대사 맥락으로 화자를 붙이고, 사용자가 리뷰에서 고칩니다. 화자 색은 화자 이름이 있을 때만 씁니다.
- **사진·무음 구간:** 사진 컷은 원본 오디오 매핑 규칙에서 제외합니다. 영상 컷은 원본 오디오 cue가 정확히 1개라는 규칙을 유지하되, 무드 구간은 그 cue의 음량을 -80dB까지 낮출 수 있습니다.
- **음원 profile(YouTube):** 완화하는 것은 플랫폼 범위(YouTube만)뿐입니다.
  - 라이선스 근거와 claim 근거는 그대로 요구합니다.
  - Content ID에 등록된 곡이라고 알려진 음원은 제외합니다.
  - CC-BY 표기는 `credits.md`에 쓰고, 영상 설명란에 붙여 넣을 문구로 제공합니다.
- **해상도:** 1080p30부터 시작하고, 4K는 이후 옵션으로 둡니다.

## 설계 원칙

- **판단은 Claude, 반복 작업은 script.** 메타데이터, proxy 생성, 전사, 음량·장면 분석, 렌더 검사는 Python helper로 고정합니다. 장면 선택, 자막 문구, 선곡은 Skill 지침에 따라 Claude가 판단합니다.
- **원본은 읽기만 합니다.** 모든 파생 파일은 `work/<run_id>/`에 만들고 hash로 추적합니다.
- **사람이 확인하는 지점은 세 곳입니다.** 후보 확정, 자막·사운드 초안 확인, 최종 미리보기. 그 사이 단계는 자동으로 이어집니다.
- **context를 아낍니다.** Claude는 원본 대신 클립별 요약 파일(전사, 음량 피크, contact sheet)만 읽습니다. 긴 영상은 5분 단위 구간으로 나눠 분석합니다.
- **기존 안전장치는 유지합니다.** run lock, fingerprint, 실패 보존, 출력 덮어쓰기 금지를 production 경로에 그대로 씁니다. synthetic 경로와 테스트는 회귀 검사로 남깁니다.

## 작업 흐름 (한 run 기준)

```
brief → ingest → analyze → scout(후보 카드) → [사용자 확정]
      → assemble(timeline v2) → caption·sound → [사용자 확인] → render → [최종 미리보기]
```

| 단계 | 하는 일 | 주체 | 산출물 (`work/<run_id>/`) |
| --- | --- | --- | --- |
| brief | 프롬프트의 유형, 톤, 60/40, 자막 80/20, 원본 폴더를 고정 | Claude | `brief.json` |
| ingest | ffprobe inventory, hash, VFR·HDR·회전 감지. 영상은 CFR 30fps 1080p SDR H.264 proxy로, HEIC는 JPG로(`sips`) 변환 | script | `sources.json`, `proxy/`, `photos/` |
| analyze | Whisper 전사(단어 타임스탬프), 음량·웃음 후보 피크(`ebur128`), 무음(`silencedetect`), 장면 전환(`scdet`), 2초 간격 contact sheet | script | `analysis/<clip>/{transcript,audio,scenes}.json`, `sheet-*.jpg` |
| scout | 클립별 요약을 읽고 `fun`·`mood` 후보를 고름. 후보마다 원본 구간, 이유, 편집 계획, 예상 길이를 작성 | Claude (Skill) | `candidates.json` |
| review | 후보마다 **기대 화면 still**(자막·효과 합성)과 짧은 미리보기 클립(480p)을 렌더해 리뷰 페이지로 보여줌 | script + Remotion | `review/index.html`, `review/<id>.jpg/.mp4` |
| 확정 | 사용자가 채팅으로 "7 채택, 3 자막만 수정, 5 제외"처럼 답함 | 사용자 | `selection.json` |
| assemble | 확정 후보를 이야기 순서로 배치. fun 장면이 흐름을 이끌고, 이동·풍경·마무리는 mood 호흡 구간으로 둠 | Claude | `timeline.json` (v2) |
| caption·sound | 자막 kind·preset 지정, BGM 구간·효과음 cue, ducking | Claude (Skill) | timeline 갱신, `audio-plan.md` |
| render | Remotion 렌더 → decode·길이·loudness QA. 긴 영상은 구간별로 렌더한 뒤 이어 붙임 | script | `preview.mp4`, `verify.json`, `credits.md` |

리뷰 카드 한 장의 구성은 다음과 같습니다.
- 머리: 후보 번호와 제목, `fun`/`mood` 태그, 원본 파일·구간 → 편집 후 길이
- 왼쪽(현재 원본): 프레임 4장과 타임코드, 핵심 대사, 선정 이유(근거 신호)
- 오른쪽(기대 화면): 자막·효과 글자를 합성한 still, 편집 계획 3줄 안팎(컷·속도·줌, 자막 preset, 효과음·BGM)
- 아래: 채택, 자막만 수정, 제외. 선택은 채팅으로 답합니다.

## 구현 단위 (순서대로, 한 번에 하나씩)

### 1. Production 범위와 데이터 계약
- `config/project.json`: `phase: "production"`, `source_roots` 허용 목록, 플래그(`asr_local`, `audio_search`, `audio_downloads`)
- `scripts/common.py`: `validate_setup_config`를 phase별 검증으로 분리합니다. synthetic은 기존 규칙을 그대로 유지하고, production은 `source_roots` 안의 경로만 허용하며 외부 업로드는 계속 금지합니다.
- 재사용: `safe_path`, `run_lock`, `write_json`, `run_command`, `read_state`, `input_fingerprint`
- timeline v2 schema 작성(`scripts/timeline_v2.py` 또는 `common.py`)
  - `sources`: id, proxy, hash
  - `clips`: source, in, out, speed, zoom/crop, transition, tag(fun/mood)
  - `captions`: kind(`dialogue`·`variety`·`situation`·`sfx_text`·`inner_voice`·`mood`·`place`), preset, position, 애니메이션
  - `audio`: original·bgm·sfx와 gain envelope
- 원본 오디오와 영상 매핑 검사, 구간 경계 검사, 연속성 검사는 기존 `validate_timeline`의 규칙을 일반화해서 씁니다.
- `.claude/settings.json`: production phase에서 `source_roots` 경로는 읽기만 허용합니다(Edit/Write deny는 유지).

### 2. Ingest
- `scripts/ingest.py --run-id ... --source <dir>`
  - ffprobe로 VFR·HDR(color_transfer `arib-std-b67`/`smpte2084`)·회전을 감지합니다.
  - proxy 변환: 기본은 VideoToolbox H.264 CFR 30fps 1080p입니다.
  - HDR 원본은 `zscale`이 없으므로 macOS 내장 `avconvert`의 SDR preset을 1순위로 검증합니다. 실패하면 FFmpeg `tonemap`으로 대체합니다.
- 사진: `sips -s format jpeg`. EXIF 회전과 촬영 시각을 기록합니다.
- 결과: 촬영 시각 순서로 정렬된 `sources.json`

### 3. Analyze
- 전사: `whisper-cli`를 `-l ko`, 단어 타임스탬프 옵션으로 실행합니다.
  - 모델 다운로드는 사용자 승인 후 진행합니다. 후보는 `large-v3-turbo` q5(약 0.6GB)와 `large-v3`(약 3GB)이고, 저장 위치는 `.tools/whisper/`입니다.
- 오디오 신호: `ebur128`로 단기 음량 피크를 잡고, 대사 사이 큰 소리를 웃음·리액션 후보로 표시합니다. `silencedetect`로 정적 구간을 찾습니다.
- 시각: `scdet` 장면 전환, 구간별 contact sheet(FFmpeg `tile`)
- 클립별 한 장짜리 요약 `analysis/<clip>/summary.md`. Claude는 이 파일만 먼저 읽습니다.

### 4. 후보 카드와 기대 화면 (사용자 최우선 요구)
- Skill이 `candidates.json`을 작성합니다. 후보마다 다음을 담습니다.
  - 원본 구간
  - 이유(근거 신호)
  - 편집 계획: 컷, 속도, 줌, 자막 문구와 preset, 효과음
  - 예상 길이
- `scripts/review.py`
  - 후보마다 Remotion `renderStill`로 기대 화면을 만듭니다(자막·효과 글자 합성).
  - 짧은 480p 미리보기 클립도 만듭니다.
  - 정적 `review/index.html`을 생성합니다.
- 기존 읽기 전용 뷰어(`scripts/studio.py`)를 확장해 리뷰 페이지와 still·clip을 loopback으로 보여줍니다. 쓰기 API는 추가하지 않고, 선택은 채팅으로 받습니다(Claude 판단).

### 5. 예능 80 · 감성 20 자막 시스템
- `renderer/src/captions/`에 preset 컴포넌트를 둡니다.
  - 예능 계열
    - `variety`: 굵은 외곽선, 팝·바운스
    - `situation`: 상황 설명 박스
    - `sfx_text`: 기울어진 효과 글자. 예: "띠용", "쾅"
    - `inner_voice`: 괄호 속마음
    - 화자별 색
  - 감성 계열
    - `mood`: 얇은 세리프, 페이드
    - `place`: 장소·시간 카드
- 폰트: OFL 라이선스 한글 폰트를 로컬에 번들합니다. 예능용은 Black Han Sans, Jua, Do Hyeon, 감성용은 Gowun Batang 등입니다. 다운로드는 승인 후 진행하고, 라이선스 파일을 함께 보관합니다.
- 80/20은 문구 수 비율 목표로 Skill이 점검합니다(강제 quota는 아님).
- 렌더 composition: synthetic 워터마크는 synthetic 전용 composition에만 남기고, production composition을 따로 둡니다.

### 6. 사운드: 사용자 음원 + Claude 무료 음원 탐색
- `assets/audio/user/`: 사용자가 넣은 파일. 출처·조건을 `config/media-licenses.json`에 등록합니다.
- Claude 탐색
  - 장면 분위기(신남, 잔잔, 긴장, 허무)별로 무료 음원 후보를 찾습니다. 출처 후보는 Pixabay Music·SFX, Freesound(CC0 위주), Incompetech(CC-BY)입니다.
  - 후보마다 라이선스 근거 URL을 기록합니다.
  - **다운로드는 후보 목록을 보여주고 사용자 승인 후** 진행합니다.
- 기존 `audio_eligibility`를 재사용하되 1차 게시 대상인 YouTube 기준으로 완화한 profile을 추가합니다. 세 플랫폼 profile은 그대로 남깁니다.
- 배치 규칙
  - BGM은 장면 묶음마다 전환하고, 대사 중에는 -12dB 이상 낮춥니다.
  - 효과음은 리액션·전환에 한정해 반복 피로를 줄입니다.
  - 무드 구간은 현장음을 살립니다.

### 7. 롱폼 렌더
- production profile: 1080p30 H.264. 4K는 이후 옵션으로 둡니다.
- concurrency·timeout 상한은 production profile에서 따로 설정합니다.
- 구간(챕터)별로 렌더하고 FFmpeg concat으로 이어 붙입니다. 구간 단위로 재렌더하고 재개합니다.
- QA: 길이, decode, loudness(YouTube 기준 약 -14 LUFS 참고), 자막이 화면 밖으로 나가지 않는지

### 8. Skill과 harness
- 반복되는 판단 영역이 확인되어 Custom Skill 3개를 추가합니다.
  - `vlog-scout`: 후보 선별 기준, 근거 표기, 카드 형식
  - `k-variety-caption`: 80/20 자막 규칙, preset 사용법, 말투 예시, 금지 사항(과장, 원본에 없는 사실)
  - `vlog-sound`: 음원 탐색, 라이선스 기록, 배치·믹싱 규칙
- `vlog-workflow` 진입 Skill(`disable-model-invocation: true`): 단계, 상태, 다음 행동을 안내합니다. `/vlog-workflow`로 시작합니다.
- `remotion-best-practices`는 그대로 사용합니다. Skill lock(`config/skills-lock.json`)과 doctor 검사에 새 Skill을 등록합니다.
- `CLAUDE.md`, `docs/workflow.md`, `docs/roadmap.md`, `feature_list.json`을 새 흐름으로 갱신합니다.

## 일반화할 때 지킬 불변식 (sharpen-refine)

기존 테스트 33개가 고정하는 동작입니다. 일반화 후에도 synthetic 경로에서 그대로 통과해야 하며, 테스트를 바꿔서 통과시키지 않습니다.
- **범위 검사:** 쓰기 진입점(create, render, 미리보기 시작)은 매번 현재 config를 다시 검사합니다. 준비·렌더 도중 범위가 바뀌면 실패를 기록하고 partial을 보존합니다(`test_scope_change_*`).
- **run 상태:** `stage`/`status` 조합, owner·run_id 일치, lock 자동 삭제 금지, SIGINT/SIGTERM 시 소유한 process group을 먼저 종료한 뒤 lock 해제(`test_sigint_*`)
- **출력 보호:** 기존 output·bundle·credit 덮어쓰기 금지, `os.link`로 확정, succeeded run 재사용은 입력·출력 hash가 맞을 때만
- **경로:** traversal, symlink, hard link 거부. 실제 원본 run ID는 파일을 읽기 전에 거부(`test_real_run_rejected_before_read`). production에서는 `source_roots` 밖 경로를 같은 방식으로 거부합니다.
- **timeline:** 길이는 선택한 컷의 합이고 고정 목표가 없습니다. 원본 오디오는 영상 컷마다 정확히 한 번 매핑되고, gain envelope는 cue 양 끝을 덮습니다.
- **뷰어:** loopback 전용, GET·HEAD만, 쓰기·WebSocket·외부 Host 거부, 스크립트 없는 페이지
  - 단, 128 MiB 메모리 snapshot은 롱폼 영상에 맞지 않습니다.
  - production에서는 검증한 파일을 APFS clone(`cp -c`)으로 읽기 전용 snapshot 사본을 만들고, 그 사본에서 byte range를 제공합니다.
  - 시작 시 hash를 검증하는 동작은 유지합니다.
- **fingerprint:** synthetic run의 fingerprint 대상 목록은 바꾸지 않습니다. 새 production 파일이 늘어나 기존 synthetic run이 stale이 되는 것은 허용합니다(문서화된 정상 동작).

## 첫 검증 sample (구현 2–4 직후)

사용자가 고른 2–3분 클립 2–3개와 사진 몇 장을 사용합니다.
- 사용자가 미리 웃긴 지점을 메모하고, Claude 후보와 비교합니다.
  - 대부분 맞히면 그대로 진행합니다.
  - 대부분 놓치면 사용자 메모를 1차 입력으로 바꿉니다.
- proxy 렌더 속도와 오디오 싱크, HDR 변환 색감을 확인합니다.

## Verification

- 매 단위: `./init.sh` PASS(기존 Python 33개·Node 2개 + 새 테스트). synthetic `./scripts/smoke-render.sh` 회귀 PASS
- 단위 1: 범위 밖 경로, symlink, 원본 쓰기 시도가 거부되는지 테스트
- 단위 2–3: 합성 HDR·VFR·HEIC fixture(FFmpeg·sips로 생성)로 proxy·분석 결과 검사
- 단위 4–5: 합성 run으로 still·review 페이지 생성, 브라우저에서 리뷰 페이지 확인
- 단위 6: 라이선스 기록이 없는 음원이 렌더에서 거부되는지
- 단위 7: 3분 합성 영상의 구간 렌더·concat 길이와 싱크
- 실제 원본 sample은 사용자가 폴더를 지정하고 승인한 뒤에만 진행합니다. 결과는 PASS / FAIL / NOT_RUN / BLOCKED로 구분해 기록합니다.

## 승인 후 진행 방식

이 계획을 `docs/superpowers/specs/2026-10-19-production-harness-design.md`에 설계 문서로 저장합니다. 이후 **단위 1부터 하나씩** 구현하고, 단위마다 결과를 보고합니다. Whisper 모델·폰트·음원 다운로드는 각 단위에서 다운로드할 파일 이름과 크기를 보여드리고 승인받은 뒤 진행합니다.
