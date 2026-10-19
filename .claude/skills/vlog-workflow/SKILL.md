---
name: vlog-workflow
description: vlog-me 제작 진입점. 사용자가 /vlog-workflow로 브이로그 제작을 시작하거나 이어갈 때 사용합니다. 현재 phase와 run 상태를 확인하고, 다음 단계(ingest·analyze·후보 리뷰·선택·조립·렌더)와 사용자 확인 지점을 안내합니다.
disable-model-invocation: true
---

# vlog-workflow

여행 영상·사진을 재미 60 · 감성 40의 YouTube 롱폼 브이로그로 편집하는 흐름을 이어 갑니다. 이 Skill은 순서와 확인 지점을 정합니다. 판단 기준은 아래 Skill과 문서에 있습니다.

- 후보 선별: `vlog-scout`
- 자막: `k-variety-caption`, [docs/caption-style.md](../../../docs/caption-style.md)
- 사운드: `vlog-sound`, [docs/sound-guide.md](../../../docs/sound-guide.md)
- 명령과 실패 처리: [docs/workflow.md](../../../docs/workflow.md)

## 1. 먼저 확인

1. `config/project.json`의 `phase`를 읽습니다.
   - `setup_synthetic_only`: 실제 원본을 열 수 없습니다. 합성 검증만 하거나, 사용자가 실제 제작을 요청하면 아래 "phase 전환"을 안내합니다.
   - `production`: `source_roots`에 적힌 `sources/<여행>/`만 읽을 수 있습니다.
2. 사용자의 이번 요청이 어느 단계까지인지 확인합니다. 요청하지 않은 다음 단계는 시작하지 않습니다.
3. 진행 중인 run이 있으면 `work/prod-*/state.json`의 `stage`·`status`·`next_action`을 읽고 이어 갑니다. lock(`.lock`)이 남아 있으면 지우지 말고 사용자에게 알립니다.

## 2. 단계와 확인 지점

| state (stage/status) | 다음 행동 | 명령 | 사용자 확인 |
| --- | --- | --- | --- |
| run 없음 | 원본 폴더 ingest | `python3 scripts/ingest.py run --source-root sources/<여행>` | 처리 못 한 파일(`skipped`), HDR 색 확인 필요 클립 보고 |
| ingested/pending | 분석 | `python3 scripts/analyze.py --run-id <run>` | 없음 |
| analyzed/pending | 후보 선별과 카드 생성 | `vlog-scout`를 따라 `candidates.json` 작성 → `python3 scripts/review.py build --run-id <run>` | **필수.** 리뷰 페이지를 열어 달라고 안내하고 답을 기다림 |
| reviewed/pending | 사용자 답을 `selection.json`으로 기록 | `python3 scripts/review.py select --run-id <run>` | 답이 모호하면 다시 질문 |
| selected/pending, `caption_edit` 있음 | 자막 수정 → 리뷰 다시 생성 | `k-variety-caption` → `review.py build` → 다시 select | **필수** |
| selected/pending | 조립 | `python3 scripts/assemble.py --run-id <run>` | `assemble-report.md`의 확인할 점 보고 |
| assembled/pending | 렌더 | `python3 scripts/render_prod.py --run-id <run>` | 사용자가 렌더를 요청했을 때만. `production_render: true` 필요 |
| render/failed·paused | 같은 명령으로 재개 | `render_prod.py` 다시 실행 | 실패 원인 보고 |
| rendered/succeeded | 시청 안내, 수정 요청 반영 | 자막·음량 같은 작은 수정은 `timeline.json`을 고치고 `render_prod.py --check` 후 다시 렌더. 장면을 넣고 빼려면 리뷰부터 다시(`review.py build` → select → assemble) | **필수.** 사람 시청 결과 |

- 모든 명령은 실패하면 state에 이유를 남깁니다. 실패한 run·partial·lock은 지우지 않습니다.
- 긴 명령(ingest·analyze·render)은 백그라운드로 실행하고, 끝나면 결과를 보고합니다.
- 렌더 제한 시간은 영상 길이에 맞춰 늘어나지만, 그래도 멈추면 같은 명령을 다시 실행해 이어서 렌더합니다. 이것은 예상된 동작입니다.
- 다시 조립(assemble)하면 직접 고친 `timeline.json`은 `timeline.prev-*.json`으로 밀려납니다. 다시 조립하기 전에 사용자에게 알립니다.
- `timeline.json`을 직접 고친 뒤에는 `python3 scripts/render_prod.py --run-id <run> --check`로 검증합니다. timeline의 자막에는 `preset`이 반드시 있어야 합니다.

## 3. phase 전환 (사용자가 명시적으로 요청할 때만)

사용자가 채팅에서 실제 제작이나 첫 sample을 요청하고, 사용할 폴더 이름을 알려줄 때만 진행합니다.

1. 원본을 `sources/<여행>/`에 두었는지 확인합니다. Claude가 원본을 옮기거나 복사하지 않습니다.
2. `config/project.json`을 `config/production.example.json` 형태로 바꾸고 `source_roots`에 그 폴더를 적습니다. `.tools/whisper/ggml-large-v3-turbo.bin` 파일이 있을 때만 `asr_model`을 그 이름으로 두고, 없으면 `null`로 둡니다(없는 모델을 적으면 분석이 실패합니다).
3. `.claude/settings.json`에서 `Read(sources/**)`와 `Bash(* sources/*)` 계열 deny만 풉니다. `Edit/Write(sources/**)` deny와 `protect_sources.py` hook은 유지합니다.
4. `audio_search`·`audio_downloads`·`production_render`는 기본 `false`입니다. 필요하면 Claude가 켜자고 제안할 수 있지만, 사용자가 채팅으로 동의한 뒤에만 `true`로 바꿉니다.
5. 바꾼 내용을 사용자에게 보여주고, 합성 검증으로 돌아갈 때는 setup 설정으로 되돌립니다(두 phase는 동시에 쓸 수 없음).

## 4. 지키는 것

- 원본(`sources/`)에는 쓰지 않습니다. 파생 파일은 모두 `work/<run>/`에 둡니다.
- 대사가 아닌 문장을 `dialogue` 자막으로 쓰지 않습니다.
- 다운로드는 production phase에서, 파일 이름·출처·크기를 보여주고 사용자가 그 파일을 승인한 뒤에만 합니다. Whisper 모델과 자막 폰트는 이미 설치되어 있습니다(`config/toolchain.json`, `config/fonts-lock.json`).
- 업로드, 외부 전송, 유료 API는 쓰지 않습니다.
- 수치 검사 통과를 사람의 시청·청취 확인으로 바꿔 말하지 않습니다. 보고는 PASS / FAIL / NOT_RUN / BLOCKED로 나눕니다.
- 작업이 끝나면 `progress.md`, `session-handoff.md`, `feature_list.json`에 상태를 남깁니다. commit은 요청할 때만 합니다.
