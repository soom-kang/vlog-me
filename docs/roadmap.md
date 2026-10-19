# 실제 제작까지의 로드맵

목표는 실제 여행 영상·사진에서 재밌는 장면과 감성 장면을 골라 예능 자막을 입힌 YouTube 롱폼 브이로그를 Claude Code 하나로 편집하는 것입니다. 이 문서는 현재 위치와 다음 단계를 여는 방법을 정리합니다. 2026-10-19 리뷰 기준입니다.

## 지금 할 수 있는 것과 없는 것

현재 phase는 `setup_synthetic_only`입니다.

할 수 있는 것:
- 환경 점검(`./init.sh`)
- FFmpeg로 만든 합성 영상·사진·테스트 톤의 렌더와 QA
- 완료된 합성 영상의 읽기 전용 미리보기

아직 할 수 없는 것:
- 실제 원본 영상·사진 읽기와 처리
- 한국어 전사(ASR), 재미·감성 장면 후보 찾기
- 예능 자막 스타일 적용
- BGM·효과음 확보와 배치
- 롱폼 길이의 렌더

`scripts/common.py`의 `validate_setup_config`는 `setup_synthetic_only`가 아니면 모든 쓰기 명령을 거부합니다. 따라서 `config/project.json`만 고쳐서는 다음 단계로 넘어갈 수 없고, 아래 단계 1의 구현이 먼저 필요합니다.

## 단계

각 단계는 한 번에 하나의 feature로 진행하고, 완료 근거를 `feature_list.json`과 `reports/`에 남깁니다. 다음 단계는 자동으로 시작하지 않습니다.

| 단계 | 내용 | 완료 기준 |
| --- | --- | --- |
| 1. 범위 전환 계약 | `real_media_sample` phase 정의. 허용 원본 폴더 1개, 클립 수 상한, 외부 전송 금지. phase별 검증 함수 분리 | 기존 합성 테스트 유지 + 새 phase 허용·거부 테스트 |
| 2. 원본 sample 검증 | ffprobe inventory, CFR 1080p SDR proxy(원본 무변경), frame contact sheet, 음량 피크 목록, 로컬 ASR 1개 | Claude가 고른 재미·감성 구간과 사용자 표시 구간 비교 보고, proxy 렌더 속도·싱크 측정 |
| 3. 예능 자막·composition | timeline v2(다중 클립, `dialogue`·`editorial`·`sfx_text` 자막), 예능 자막 컴포넌트, 라이선스 확인한 한글 폰트 | sample 편집안의 자막을 사용자가 보고 승인 |
| 4. 사운드·롱폼 렌더 | 사용자가 직접 받은 음원을 권리 근거와 함께 등록(1차 게시 대상인 YouTube 이용 조건부터 확인), ducking·효과음 배치, 롱폼 timeout·분할 렌더 | 사람 시청·청취 검수 기록 |

단계 2의 가장 큰 불확실성은 "Claude가 재밌는 포인트를 찾을 수 있는가"입니다. 웃음은 대사·타이밍·리액션 소리에 몰려 있어 frame만으로는 부족합니다. 비교 결과 자동 후보가 사용자 표시를 대부분 놓치면, 사용자가 남긴 타임스탬프 메모를 1차 입력으로 쓰는 방식으로 바꿉니다.

## 단계를 여는 프롬프트 예

단계 1을 시작할 때 Claude Code에 다음처럼 요청합니다.

```text
docs/roadmap.md의 단계 1(범위 전환 계약)을 시작해줘.
- 이번에는 코드·config·테스트만 바꾸고 실제 원본은 열지 마.
- 허용할 원본 폴더 후보는 <경로>이고, sample 클립은 최대 3개야.
- ASR model·음원 다운로드는 하지 마.
- 기존 합성 테스트와 ./scripts/smoke-render.sh가 계속 통과해야 해.
```

단계 2부터는 원본 접근과 model 다운로드가 포함됩니다. 요청에 허용 폴더, 클립, 다운로드할 model 이름을 직접 적어 범위를 명시합니다. ASR model 후보와 선택 기준은 단계 2를 시작할 때 Claude Code가 제안하고 사용자가 고릅니다.

## 용어

- **brief**: 한 run의 제작 설정을 고정한 `brief.json`.
- **fingerprint**: 입력·코드·설정 파일 hash를 묶은 값. 바뀌면 이전 결과를 다시 쓰지 않습니다.
- **stale**: 저장된 fingerprint와 현재 파일이 다른 상태. 코드가 바뀐 뒤 과거 run의 stale은 정상입니다.
- **gain envelope**: cue 안의 frame별 음량(dB) 지점. fade와 ducking(대사 중 BGM 낮추기)을 표현합니다.
- **dBTP**: true peak 음량 단위. 현재 -1 dBTP는 합성 테스트 상한이며 플랫폼 납품 기준이 아닙니다.
- **proxy**: 편집·렌더용으로 변환한 사본. 원본은 바꾸지 않습니다.
