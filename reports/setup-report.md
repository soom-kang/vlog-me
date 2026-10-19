# vlog-me 환경 구축 보고서

후속 변경: native Studio 실행을 읽기 전용 영상 뷰어로 교체했습니다. 현재 시작·미리보기 동작과 증거는 [전환 보고서](preview-only-review.md)를 기준으로 합니다. 아래 기록은 해당 검토 시점의 사실입니다.

기준일: 2026-10-18 · Asia/Seoul

이 문서는 최초 구축 시점의 기록입니다. 현재 코드의 수정 사항·테스트·최신 run은 [적대적 검토 보고서](adversarial-review.md)를 기준으로 합니다. 아래 과거 실행 근거는 보존했습니다.

## 결과와 범위

**Claude Code 단독으로 시작할 수 있는 기반 환경과 합성 검증 경로를 구축했습니다.** 기존 공식 Skill을 우선했고 새 Custom Skill·subagent·automation은 만들지 않았습니다. 브이로그 유형·톤은 제작별 prompt에서 정하고, 완성본 길이는 내용으로 결정합니다.

실제 원본 영상·사진은 읽거나 처리하지 않았고, 음악·효과음을 다운로드하지 않았습니다. 테스트 영상·사진·220/440/880 Hz 오디오는 FFmpeg로 직접 생성했습니다. 음원 목록은 비어 있고 ASR model도 설치하지 않았습니다. 이번 작업은 현재 설계의 환경 구축이며 최근 30일 전체 업무 조사나 자동화 후보 발굴은 수행하지 않았습니다.

## 설치·재사용한 구성

| 구성 | 실제 상태 | 근거 |
| --- | --- | --- |
| Claude Code | 기존 2.1.302 사용 | doctor, 실제 CLI 실행 |
| Node / npm | 프로젝트 내부 24.22.0 / 11.19.1 | `.tools/` receipt; 공식 배포 checksum 대조 |
| FFmpeg / ffprobe / Python | 기존 9.0.2 / 9.0.2 / 3.15.0 사용 | doctor |
| Remotion / React | 4.0.536 / 19.3.1 | `renderer/package.json`, lockfile |
| Browser | 프로젝트 내부 Chrome for Testing 157.0.8080.0 | `.tools/browser.json`, 실제 렌더 |
| 기존 Skill | 공식 `remotion-best-practices` 1개, 원문 유지 | `config/skills-lock.json`, 143개 파일 hash |
| Custom Skill / Subagent / Automation | 생성·활성화 0개 | 현재 프로젝트 파일 |

Skill source는 [remotion-dev/skills](https://github.com/remotion-dev/skills/tree/1441a11e95db35443bd76bb318386c0d3ca00053/skills/remotion-best-practices), 고정 ref는 `1441a11e95db35443bd76bb318386c0d3ca00053`입니다. 세부 version은 [toolchain](../config/toolchain.json)을 기준으로 합니다. 업데이트 시 재검증해야 합니다.

Watch는 전사 backend·model·cache·전송 경로를 다음 단계에서 확정하므로 설치하지 않았습니다. `video-use`와 `broll-me`도 현재 필수 경로에서 제외했습니다. 반복 판단 절차의 누락이 아직 확인되지 않아 Custom Skill 대신 프로젝트 지침과 작은 검사 script를 사용했습니다.

## 구현한 동작

- `CLAUDE.md` → 상태·인수인계 → `init.sh`의 시작 절차와 완료 기준.
- 원본 경로를 받지 않는 합성 asset 생성, hash 기반 inventory, 단일 timeline과 내용에 따른 길이 계산.
- 영상·사진·한국어 caption·원음/BGM/SFX 테스트 톤 합성, fade·ducking.
- traversal·symlink·hard link·미등록 asset 거부, 기존 출력 보존, exclusive run lock.
- 입력·코드·설정 또는 출력 변경 감지, 성공 결과 재사용, 실패·partial·stale 결과 보존.
- H.264/AAC·해상도·길이·decode·최종 오디오 수치 검사와 출력 hash 기록.

영상의 원음은 Video에서 mute하고 Audio cue로 한 번 포함합니다. 검토 중 전체 원음 cue 개수만 비교하면 첫 컷 원음 중복과 둘째 컷 원음 누락이 통과하는 문제를 재현했습니다. 컷별 시작·길이·source trim을 원음 cue와 일대일 대조하도록 수정하고 회귀 테스트를 추가했습니다.

## 검증 결과

| 검사 | 결과 | 실행 근거 |
| --- | --- | --- |
| `./init.sh` | PASS | 도구·scope·Skill hash·의존성, Python 7개 테스트, compileall, ESLint, TypeScript, Node 2개 테스트. [로그](local-verification-complete.log) |
| Shell 진입점 | PASS | 실행 권한과 `bash -n` 문법 검사 |
| Claude Code의 Skill 등록 | PASS | 실제 CLI에서 Skill 노출, reference 읽기, scope·길이 정책 확인. [기록](claude-skill-check.json) |
| 최초 restricted mode 확인 | PARTIAL | 파일 읽기는 통과했으나 slash command 노출 미확인. 일반 프로젝트 mode로 분리 검증. [기록](claude-check.json) |
| 합성 렌더 | PASS | 6초와 14초 길이, 한국어 caption 수정, 다중 audio cue 연결; 최종 코드 run은 아래 참조 |
| 상태·실패 검사 | PASS | 입력/출력 변경, partial/running, 경로 alias, 덮어쓰기, 미등록 asset, 원음 중복·누락, 권리 unknown 거부 |
| 성공 결과 재개 | PASS | 같은 run의 status/render 재호출 후 출력 mtime 유지와 lock 해제. [기록](resume-check.json) |
| Harness 구조 | PASS, 100/100 | instructions·state·verification·scope·lifecycle 각각 5/5. [구조 검사](harness-assessment.json) |

최종 코드에서 성공한 run은 `synthetic-20261018-143016-f8b2d6f7`입니다. 12초 테스트 영상과 2초 사진을 합쳤고 첫 렌더 전에 caption을 수정했습니다. [run 기록](final-run.json), [QA](../work/synthetic-20261018-143016-f8b2d6f7/verify.json), [preview](../work/synthetic-20261018-143016-f8b2d6f7/preview.mp4), [frame](../work/synthetic-20261018-143016-f8b2d6f7/frame.png)을 보존했습니다.

Harness 최초 구조 검사는 state 4/5로 가장 낮았습니다. 인수인계에 변경 파일과 남은 제한을 명시한 뒤 다섯 항목 모두 5/5가 되었습니다. 이 점수는 문서 구조 검사이며 실제 편집 품질이나 agent 성능 benchmark가 아닙니다.

- 출력: 14초, 1280×720, H.264/AAC, 420 frames.
- 렌더·검사 구간: 35.84초. 초기 설치·fixture 생성 시간은 제외합니다.
- child 최대 RSS: 1,204,846,592 bytes. 전체 process tree의 동시 peak가 아닙니다.
- QA 시점 run artifact: 67,922,278 bytes. 공용 runtime·dependency 용량은 제외합니다.
- 저장된 preview 측정값: -25.34 LUFS, true peak -18.21 dBTP. 테스트이므로 납품 음량 목표를 확정하지 않습니다.

`verify.json`의 `input_*`는 저장된 preview 측정값이고 `output_*`는 loudnorm 분석의 예상 출력값입니다. 실제 preview에 정규화를 적용했다는 뜻이 아닙니다. true peak 검사 상한 -1 dBTP는 setup 기준이며 플랫폼 납품 규칙이 아닙니다. frame을 열어 한국어 수정 문구 표시를 확인했으며 사람의 전체 시청·청취를 완료했다는 의미는 아닙니다.

과거 PASS run도 이후 코드가 바뀌면 `status`에서 stale이 정상입니다. 현재 코드의 검증으로 과거 run을 재사용하지 않습니다. Claude 읽기 확인 두 번의 CLI 보고 비용 합계는 약 USD 0.348이며 원본·음원을 model에 전달하지 않았습니다.

## 발견한 실패와 처리

| run suffix | 관찰 결과 | 처리 |
| --- | --- | --- |
| `141612-1bf066ea` | sandbox localhost port 사용 실패 | 해당 합성 렌더 범위의 실행 권한으로 재검증 |
| `141910-188c0689` | Chrome Headless Shell 시작 timeout | 같은 bundle에서 Chrome for Testing 비교 성공; 활성 browser 변경 |
| `142453-8f82ee57` | 렌더 중 구현 코드 수정으로 fingerprint 불일치 | 의도하지 않은 중간 수정. 완성 출력 확정을 거부한 partial 보존 후 새 run |
| `142455-6faa8c59` | non-login shell에서 FFmpeg PATH 누락 | `env.sh`에 기존 Homebrew 경로 연결; 이후 생성 실패도 state 기록 |

전체 ID는 `synthetic-20261018-`와 suffix를 연결합니다. 실패 폴더와 browser 비교 기록을 보존했습니다. 전역 설정 변경이나 실패 출력 덮어쓰기로 해결하지 않았습니다. process 목록 조회는 sandbox에서 거부되어 사용하지 않았고 완료 판정은 실행 결과와 파일 검사로 했습니다.

## 미검증·보류 범위

| 항목 | 상태 | 다음에 필요한 근거 |
| --- | --- | --- |
| 원본 ingestion·VFR/HDR/HEIC·시각 매핑 | NOT_IMPLEMENTED / NOT_RUN | 허용된 원본 sample |
| 한국어 ASR·장면 탐색·이야기 선별 | NOT_INSTALLED / NOT_RUN | backend/model 선택과 대표 입력 평가 |
| 예능 caption 취향·사운드 밀도 | NOT_RUN | 실제 장면 비교와 사용자 시청·청취 |
| 무료 음원·세 플랫폼 권리 | NOT_RUN | 실제 후보의 license와 claim 근거; 현재 목록 비어 있음 |
| Studio UI 조작 | NOT_RUN | 진입점 문법만 검사; 개별 JSX 편집은 지원하지 않음 |
| 장시간·4K 성능 | NOT_RUN | 짧은 720p 합성 sample만 측정 |
| 업로드·Content ID·플랫폼 확인 | NOT_RUN | 현재 실행 범위 아님 |
| 새 Skill A/B 평가 | Not applicable | Custom Skill 생성·기존 Skill 수정 없음 |

음원 적격성 함수는 상태 검사이며 권리 사실 확인·영구 무claim 보장이 아닙니다. 180초 timeout과 concurrency 2는 합성 setup 범위이며 장시간 제작 성능을 보장하지 않습니다.

## 저장소·운영 상태

시작·종료 시 이 폴더는 Git repository가 아니었습니다. `git status --short`는 exit 128을 반환하므로 Git diff 대신 작성 파일·계약·실행 근거를 검토했습니다. Git init·commit·push·scheduler·외부 메시지 전송은 하지 않았습니다. 작성한 문서의 로컬 링크, JSON 구문, shell 문법과 알려진 credential 패턴을 확인했으며 끊어진 링크나 해당 secret 패턴은 발견하지 않았습니다.

기존 설계 문서를 보존하고 구축 전 상태라는 안내와 현재 문서 링크만 갱신했습니다. harness·설정·renderer·tests·reports를 프로젝트 안에 추가했습니다. 다른 프로젝트, 전역 shell 설정, credential과 `.env`는 변경하지 않았습니다. `.tools/`, `.cache/`, `renderer/node_modules/`, `work/`는 로컬 실행 자료로 `.gitignore`에서 제외합니다.

`change_risk`는 로컬 dependency·browser 실행·파일 쓰기를 포함하는 moderate입니다. 원본·외부 시스템 변경은 없고 경로·소유권·실패 복구 검사가 필요합니다. `execution_advice`는 standard / measured이며 모델 설정을 변경하지 않았습니다. 실제 원본·유료 provider·게시가 추가되면 노출 범위와 검증 계획을 다시 평가합니다.

permission patterns와 helper는 OS sandbox가 아닙니다. `CLAUDE.md`에 허용 범위와 직접 shell을 통한 우회 금지를 명시했습니다. 다음 세션은 현재 결과 설명이나 합성 테스트를 할 수 있으며 보류된 실제 제작을 자동으로 시작하지 않습니다.
