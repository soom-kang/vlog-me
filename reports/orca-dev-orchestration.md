# orca-dev-orchestration 보고서 (2026-10-22)

설계: [2026-10-22-orca-multi-agent-design.md](../docs/superpowers/specs/2026-10-22-orca-multi-agent-design.md) · 계획: [2026-10-22-orca-multi-agent.md](../docs/superpowers/plans/2026-10-22-orca-multi-agent.md) · 사전 확인: [orca-spike-2026-10-22.md](orca-spike-2026-10-22.md)

Claude 단일 세션에서 구현했습니다. 구현에는 Orca worker나 Codex를 쓰지 않았습니다. 구현 뒤 사용자 요청으로 실패 receipt 확인용 Run 1개를 돌렸습니다(가짜 모델 ID, 파일 변경 없음). 원본 미디어는 읽지 않았습니다.

## 결과

| Task | 결과 | 근거 |
| --- | --- | --- |
| 0. feature 등록 | PASS | `feature_list.json`(`orca-dev-orchestration`, `first-real-sample` on_hold), `./init.sh` PASS |
| 1. 사전 확인 | 부분 PASS | 모델 ID·setup 위치·worktree 검증·실패 receipt PASS. 한도 메시지 공식 문구 NOT_RUN |
| 2. 규칙 범위 분리 | PASS | `CLAUDE.md`, `docs/workflow.md` |
| 3. `AGENTS.md` | PASS | 저장소 루트 |
| 4. 운영 문서 | PASS | `docs/orca.md` |
| 5. 지시문 템플릿 | PASS | `docs/orca/` 4개 |
| 6. worktree 설정·dev 검증 | PASS | `orca.yaml`, `scripts/dev-check.sh`, `scripts/dev_tests.py`, `.gitignore` |
| 7. 테스트 | PASS | `tests/test_orca_harness.py` 6개 |
| 8. 기록 | PASS | 이 보고서, `progress.md`, `session-handoff.md` |

## 검증

- main checkout `./init.sh`: PASS(Python 158개, skip 6, lint·typecheck·node test).
- 임시 git worktree(원본·음원 없음, `.tools`·`renderer/node_modules` symlink, 현재 변경 복사)에서 `./scripts/dev-check.sh`: PASS(157개, skip 6). 확인 뒤 worktree 제거.
- `use_subagents`, `config/`, `scripts/production.py`, `scripts/common.py`: 변경 없음.

## 계획과 달라진 점

- `scripts/orca-setup.sh` 대신 Orca 기본 기능인 `orca.yaml`의 `worktree.sharedDirectories`를 씁니다.
- worktree에서는 doctor와 live-config 테스트가 원래 통과할 수 없습니다(원본 없음). 그래서 worktree 검증용 `scripts/dev-check.sh`를 따로 두고, 전체 `./init.sh`는 병합 뒤 main에서 실행합니다.

## 남은 한계

- 한도 초과 자동 fallback은 실제 한도 상황에서 검증하지 않았습니다. 감지 문구는 추정값이며 운영하면서 보강합니다.
- 격리는 OS 수준이 아닙니다(worktree에 미디어 없음 + `AGENTS.md` + 병합 전 경로 확인).
- vlog-me는 2026-10-22 Orca repo로 등록했습니다. `orca.yaml` 신뢰 승인은 아직이며 사용자가 할 일입니다.
- 실제 개발 작업으로 Orca Run을 돌린 적은 없습니다. 실패 receipt 확인용 Run(`run_12a0988c895f`)과 실패한 Task 기록은 Orca에 남아 있습니다.

## 다음 허용 행동

- 사용자가 Orca에서 `orca.yaml`을 승인합니다.
- 첫 실제 Orca Run은 사용자가 개발할 기능을 지정해 요청할 때 시작합니다.
