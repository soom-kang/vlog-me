# Claude Code 시작과 첫 작업 프롬프트

첫 작업은 **환경 점검과 현재 상태 확인까지만** 진행합니다. Claude Code를 연 뒤 아래 프롬프트를 붙여 넣으면 됩니다.

## 1. Claude Code 시작

터미널에서 실행합니다.

```bash
cd /Users/soom.kang/Desktop/work/2.services/vlog-me
./scripts/claude.sh
```

`claude.sh`는 프로젝트 폴더와 로컬 Node/npm 환경을 Claude Code에 전달합니다. `init.sh`는 아래 프롬프트에 따라 Claude Code가 실행하므로 터미널에서 미리 실행할 필요는 없습니다.

## 2. 첫 작업용 프롬프트

아래 내용을 Claude Code에 그대로 붙여 넣습니다.

```text
vlog-me의 첫 작업을 시작해줘. 이번 작업은 환경 점검과 현재 상태 확인까지만 진행해.

작업 원칙:
- Claude Code 단독으로 진행하고 기존 프로젝트 Skill을 우선해.
- 실제 원본 영상·사진에 접근하거나 처리하지 마.
- 음원·효과음·ASR model을 다운로드하지 마.
- 이번에는 새 합성 영상 생성, 렌더, 미리보기 서버 실행도 하지 마.
- 오류가 발견되면 자동 설치·설정 변경·코드 수정 없이 원인과 필요한 조치를 보고해.
- 기존 상태·출력·lock·실패 기록을 보존해.

다음 순서로 확인해:
1. CLAUDE.md, progress.md, feature_list.json,
   session-handoff.md, docs/workflow.md를 읽고 현재 범위를 파악해.
   최신 검증 근거는 reports/preview-only-review.md를 확인해.
   실제 제작까지의 단계는 docs/roadmap.md에서 확인해.

2. config/project.json에서 다음 조건을 확인해:
   - agent_runtime: claude-code
   - phase: setup_synthetic_only
   - use_subagents: false
   - source_roots: []
   - audio_downloads, external_processing, production_render, upload: false
   - runtime_policy: content_driven
   - target_duration_seconds: null

3. ./init.sh를 실행해 도구·Skill 무결성·tests·lint·typecheck를 확인해.
   실패한 단계 이후 실행되지 않은 검사는 NOT_RUN으로 구분해.

4. 기존 remotion-best-practices Skill이 현재 세션에서
   인식되고 읽히는지 확인해. Skill의 예제 명령은 실행하지 마.
   native Remotion Studio는 사용하지 않는다는 프로젝트 지침을 유지해.

5. session-handoff.md에 기록된 최신 합성 run ID를 사용해
   python3 scripts/synthetic.py status --run-id RUN-ID
   명령으로 저장된 상태를 조회해.
   stale이나 실패가 나오면 기록만 보고하고 복구·재렌더하지 마.
   코드 변경 이후의 과거 PASS run은 stale이 정상이므로 FAIL로 분류하지 마.

결과는 한국어로 간결하게 정리해:
- 검사별 PASS / FAIL / NOT_RUN / BLOCKED와 근거
- 현재 가능한 작업과 아직 구현·검증되지 않은 작업
- 문제가 있다면 필요한 조치
- 다음에 진행할 수 있는 가장 작은 작업 1개

브이로그 유형·톤은 이후 제작 프롬프트에서 정하고,
완성본 길이를 임의로 고정하지 마.
보고가 끝나면 다음 단계를 자동으로 실행하지 말고 종료해.
```

## 3. 점검 결과 확인

- 실제 실행한 검사와 과거 보고서의 결과를 구분해 확인합니다.
- 실패·누락이 있으면 원인과 필요한 조치부터 확인합니다. 코드가 바뀐 뒤 과거 run의 `stale`은 정상이며 실패가 아닙니다. 자동 복구나 재렌더는 첫 작업에 포함하지 않습니다.
- 점검이 통과해도 원본 처리·음원 다운로드·제작 작업을 시작할 권한이 생기는 것은 아닙니다. 다음 작업은 별도 요청으로 정합니다.

`init.sh`는 로컬 검사 중 임시 테스트 파일·컴파일 cache를 만들 수 있습니다. 미디어 생성·렌더·음원 다운로드·model 호출은 하지 않습니다.

현재 상태는 [인수인계 문서](../session-handoff.md), 작업별 실행 범위는 [작업 절차](workflow.md), 구현된 미리보기의 검증 근거는 [전환 보고서](../reports/preview-only-review.md)를 확인합니다.
