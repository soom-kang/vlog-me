# 실제 제작까지의 로드맵

목표는 실제 여행 영상(mp4)과 아이폰 사진에서 재밌는 장면과 감성 장면을 골라 YouTube 롱폼 브이로그를 Claude Code 하나로 편집하는 것입니다. 내용은 재미 60 · 감성 40, 자막은 예능 80 · 감성 20입니다. 승인된 설계는 [production harness 설계](superpowers/specs/2026-10-19-production-harness-design.md)에 있습니다. 이 문서는 현재 위치와 다음 단위를 여는 방법만 정리합니다.

## 현재 위치 (2026-10-19)

현재 phase는 `setup_synthetic_only`입니다. 단위 1–6(범위·데이터 계약, Ingest, Analyze, 후보 카드·기대 화면, 자막 preset, 사운드)을 구현했지만 phase는 아직 바꾸지 않았습니다. 그래서 실제 원본에는 아직 실행되지 않습니다.

할 수 있는 것:
- 환경 점검(`./init.sh`)
- 합성 영상·사진·테스트 톤의 렌더와 QA, 읽기 전용 미리보기
- production 계약 검사: `scripts/production.py`의 범위 검증, `prod-*` run 경로, `sources/` 경로 검사, timeline v2 검증
- 합성 fixture 검증: `./scripts/smoke-media.sh`(HDR·VFR·세로·무음 영상, 큰 소리·장면 전환, 한국어 합성 음성, HEIC, 테스트 톤 음원을 임시 폴더에서 생성해 ingest·분석·후보 카드·ducking 렌더)

아직 할 수 없는 것:
- 실제 원본 ingest·분석(phase 전환 필요)
- 실제 음원 확보(사용자 파일 또는 승인한 다운로드), 최종 timeline 조립, 롱폼 렌더

## 두 phase는 서로 배타적입니다

- `setup_synthetic_only`: 합성 run만 생성·렌더합니다. production helper는 모두 거부합니다.
- `production`: `sources/<여행이름>/` 안의 원본만 읽습니다. 합성 run 생성·렌더는 거부합니다. 합성 회귀 검사는 테스트의 임시 config로 실행됩니다.

production으로 바꾸려면 사용자가 채팅으로 명시적으로 요청해야 합니다. 요청을 받으면 Claude Code가 다음을 함께 바꿉니다.
1. `config/project.json`: `config/production.example.json`의 형태로 교체하고, `source_roots`에 실제 폴더를 적습니다.
2. `.claude/settings.json`: `Read(sources/**)`와 `Bash(* sources/*)` deny를 풀어 원본을 읽을 수 있게 합니다. `Edit/Write(sources/**)` deny와 `protect_sources.py` hook은 유지합니다.

## 구현 단위

각 단위는 한 번에 하나씩 진행하고, 완료 근거를 `feature_list.json`과 `reports/`에 남깁니다. 다음 단위는 자동으로 시작하지 않습니다.

| 단위 | 내용 | 상태 |
| --- | --- | --- |
| 1. 범위·데이터 계약 | production 범위 검증, `prod-*` run, `sources/` 경로 검사, timeline v2, 원본 보호 hook | 완료 |
| 2. Ingest | ffprobe inventory, VFR·HDR·회전 감지, CFR 1080p SDR proxy, HEIC→JPG | 완료(합성 fixture). HDR 색감은 실제 영상으로 눈 확인 필요 |
| 3. Analyze | 로컬 Whisper 전사, 음량·웃음 후보 피크, 무음, 장면 전환, contact sheet, 클립 요약 | 완료(합성 fixture). 실제 대화·웃음 탐지 품질은 sample로 확인 필요 |
| 4. 후보 카드·기대 화면 | 후보별 이유와 편집 계획, 자막을 합성한 still, 960×540 미리보기, 리뷰 페이지, 선택 기록 | 완료(합성 fixture). 기본 자막 preset은 시스템 폰트 |
| 5. 예능 80 · 감성 20 자막 | preset 14종 레지스트리, OFL 한글 폰트 5종 번들, 글자 수·비율 검사, [자막 가이드](caption-style.md) | 완료(합성 fixture). 실제 영상에서 취향 조정 필요 |
| 6. 사운드 | 음원 라이브러리 등록·검사(`audio_library.py`), YouTube 기준 사용 판정, 대사 ducking·효과음 밀도 규칙, 미리보기에 BGM·효과음 반영, [사운드 가이드](sound-guide.md) | 완료(합성 fixture). 실제 음원 0개, 청취 미실행 |
| 7. 롱폼 렌더 | 1080p30 구간 렌더와 이어 붙이기, QA | 대기 |
| 8. Skill·harness | `vlog-workflow`, `vlog-scout`, `k-variety-caption`, `vlog-sound` | 대기 |

단위 2–4 직후 첫 sample을 검증합니다. 사용자가 고른 2–3분 클립 2–3개를 씁니다. 사용자가 미리 웃긴 지점을 메모해 두고 Claude 후보와 비교합니다. 자동 후보가 메모를 대부분 놓치면 사용자 메모를 1차 입력으로 바꿉니다.

## 다음 단위를 여는 프롬프트 예

```text
docs/roadmap.md의 단위 7(롱폼 렌더)을 시작해줘.
- 이번에는 코드와 합성 fixture 테스트만 만들고 실제 원본은 열지 마.
- phase는 아직 setup_synthetic_only로 둬.
- 기존 테스트와 ./scripts/smoke-render.sh가 계속 통과해야 해.
```

실제 원본을 처음 읽을 때는 production 전환과 원본 폴더 이름을 함께 요청합니다. Whisper 모델·폰트·음원 다운로드는 해당 단위에서 파일 이름과 크기를 보여드리고 승인받은 뒤 진행합니다.

## 용어

- **brief**: 한 run의 제작 설정을 고정한 `brief.json`.
- **fingerprint**: 입력·코드·설정 파일 hash를 묶은 값. 바뀌면 이전 결과를 다시 쓰지 않습니다.
- **stale**: 저장된 fingerprint와 현재 파일이 다른 상태. 코드가 바뀐 뒤 과거 run의 stale은 정상입니다.
- **proxy**: 편집·렌더용으로 변환한 사본. 원본은 바꾸지 않습니다.
- **timeline v2**: production 편집의 render 입력. 여러 원본 클립, `fun`/`mood` 태그, 예능·감성 자막 kind, 원본음·BGM·효과음 cue를 담습니다.
- **gain envelope**: cue 안의 frame별 음량(dB) 지점. fade와 ducking(대사 중 BGM 낮추기)을 표현합니다.
- **dBTP**: true peak 음량 단위. 현재 -1 dBTP는 합성 테스트 상한이며 플랫폼 납품 기준이 아닙니다.
