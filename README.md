# vlog-me

Claude Code 하나에서 Skills와 프로젝트 harness를 사용해 롱폼 여행 브이로그(감성 95 · 예능 5, 풍경과 구어체 감성 자막 중심, [하우스 스타일](docs/house-style.md))를 편집하는 로컬 환경입니다. ingest부터 후보 리뷰, 조립, 롱폼 렌더까지 구현했고 **합성 영상으로만 검증**했습니다. 실제 영상은 `/vlog-workflow`로 시작하며, 첫 sample 방법은 [로드맵](docs/roadmap.md)에 있습니다.

## 시작

처음 사용하는 경우 **[Claude Code 시작 방법과 첫 작업용 프롬프트](docs/getting-started.md)**를 따라 환경 점검부터 진행합니다.

```bash
cd /Users/soom.kang/Desktop/work/2.services/vlog-me
./scripts/claude.sh
```

Claude Code가 열리면 연결된 문서의 프롬프트를 붙여 넣습니다. `init.sh` 실행과 기존 합성 run의 상태 조회까지만 진행하며, 실제 원본 접근·처리와 음원 다운로드는 하지 않습니다. 새 합성 영상 생성·렌더·미리보기 서버 실행도 첫 작업에서 제외합니다.

`claude.sh`는 프로젝트 폴더와 로컬 Node/npm PATH를 Claude Code에 전달합니다. `init.sh`만 실행한 뒤 일반 `claude`를 시작하면 앞선 script의 PATH가 부모 shell에 남지 않습니다. 별도 agent나 권한 우회 옵션은 추가하지 않습니다.

## 현재 가능한 작업

- 프로젝트 Skill: `/vlog-workflow`(진입), `vlog-scout`(후보), `k-mood-caption`(자막), `vlog-sound`(사운드)
- 프로젝트 도구, 공식·프로젝트 Skill, 번들 폰트의 무결성 검사
- 직접 생성한 영상·사진·테스트 톤의 inventory와 hash 확인
- 단일 timeline으로 영상·사진·한국어 기본 caption·원음/BGM/SFX 테스트 톤 합성
- gain envelope를 통한 fade·ducking, 출력 decode·길이·stream·loudness 검사
- 기존 출력 보호, 실패 기록, 입력 변경 시 stale 판정, 성공 결과의 hash 기반 재개

실제 장면 선별·ASR·예능 자막 스타일 완성·음원 선곡·업로드는 아직 구현하거나 검증하지 않았습니다. 전사 backend와 model은 원본 처리 범위가 허용된 뒤 선택합니다.

## 합성 검증

아래 명령은 합성 검증을 별도로 요청했을 때 사용합니다. 첫 환경 점검에는 포함하지 않습니다.

```bash
./scripts/smoke-render.sh
./scripts/smoke-render.sh --seconds 12
```

각 실행은 새로운 `work/synthetic-*` 폴더를 만듭니다. `--seconds`는 테스트 영상 길이이며 사진 2초가 추가됩니다. 본편 길이 제한이 아닙니다. 결과는 `preview.mp4`, `frame.png`, `verify.json`, `audio-credits.md`, `state.json`입니다. 테스트 톤이 포함되므로 일반 시청 콘텐츠로 사용하지 않습니다.

```bash
python3 scripts/synthetic.py status --run-id synthetic-RUN-ID
python3 scripts/inventory.py --run-id synthetic-RUN-ID
./scripts/studio.sh synthetic-RUN-ID
```

실제 run ID로 바꿔 실행합니다. `studio.sh`는 검증된 완료 영상만 보여주는 읽기 전용 뷰어입니다. 출력된 `http://127.0.0.1:PORT/` 주소를 열고, 확인 후 terminal에서 Ctrl-C로 종료합니다. `./scripts/npm.sh run studio -- RUN-ID`도 같은 뷰어를 엽니다.

native Remotion Studio는 실행하지 않습니다. 화면에는 영상 재생·탐색·음량·전체화면만 있고 agent·편집·설치·렌더 API가 없습니다. 서버는 loopback에만 연결되며 화면과 검증된 영상 외 파일은 제공하지 않습니다. 뷰어 실행은 state·props·출력을 수정하거나 렌더·model을 실행하지 않습니다.

완료·hash 검증을 통과한 저장본을 메모리에서 재생합니다. 실행 중 timeline을 바꿔도 화면은 갱신되지 않습니다. Claude Code에서 새 run의 timeline을 수정하고 렌더한 뒤 그 run을 열어 확인합니다. 이전 `--refresh`는 안내 메시지와 함께 exit 2로 종료하고, 기존 props·영상은 그대로 보존합니다. 현재 합성 뷰어의 메모리 한도는 영상 파일 128 MiB이며 본편 길이 제한이 아닙니다.

## 도구와 재설치

- Node 24는 `.tools/`에 설치되어 있고 진입점에서만 PATH에 추가됩니다. 전역 shell 설정은 바꾸지 않습니다.
- FFmpeg·ffprobe·Python·Claude Code는 기존 설치를 사용합니다. 경로·version은 `config/toolchain.json`과 doctor 출력에서 확인합니다.
- Remotion 의존성은 `renderer/package-lock.json`, 공식 Skill의 source/ref/hash는 `config/skills-lock.json`으로 고정합니다.
- 새 macOS arm64 환경에서는 `python3 scripts/bootstrap-node.py`, `./scripts/npm.sh ci --ignore-scripts`, `./scripts/npm.sh run browser` 순서로 명시적으로 설치합니다. 다른 OS는 Node 24를 PATH에 제공해야 하며 아직 검증하지 않았습니다.
- `init.sh`는 설치·네트워크 다운로드·model 실행을 하지 않습니다. 렌더에는 localhost 서버와 browser 실행 권한이 필요합니다.

## 문서

- [Claude Code 시작 방법과 첫 작업용 프롬프트](docs/getting-started.md)
- [작업 절차와 계약](docs/workflow.md)
- [실제 제작까지의 로드맵](docs/roadmap.md)
- [편집·사운드 기준](docs/editorial-guide.md)
- [구축 검증 보고서](reports/setup-report.md)
- [미리보기 전용 전환 검증](reports/preview-only-review.md)
- [이전 적대적 검토](reports/adversarial-review.md)
- [환경 설계](docs/superpowers/specs/2026-10-18-vlog-environment-design.md)
- [다음 세션 인수인계](session-handoff.md)

Git 저장소로 관리합니다. commit·push는 명시적으로 요청할 때만 합니다. `.gitignore`가 원본·음원·의존성·파생 미디어를 제외합니다.
