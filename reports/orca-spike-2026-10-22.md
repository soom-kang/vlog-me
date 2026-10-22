# Orca 사전 확인(spike) 2026-10-22

계획: [Task 1](../docs/superpowers/plans/2026-10-22-orca-multi-agent.md). Orca 1.4.237, codex-cli 0.163.0, Claude Code 2.1.306.

| 항목 | 결과 | 근거 |
| --- | --- | --- |
| 1. 모델 ID·effort | PASS | 아래 표 |
| 2. 한도 초과 메시지 형식 | NOT_RUN(공식 문구 미검증) | 아래 |
| 3. 실패 receipt 모양 | PASS | 아래(2026-10-22 사용자 요청으로 실행) |
| 4. setup hook 위치 | PASS | 아래 |
| 5. worktree에서 검증 | 부분 PASS | 아래 |

## 1. 모델 ID와 effort

| 역할 | `--agent` | `--model` | `--effort` | 근거 |
| --- | --- | --- | --- | --- |
| coordinator·plan | `claude` | `claude-opus-5-5` | `medium` | Claude 모델 ID 공식 표기 |
| 독립 review | `claude` | `claude-sonnet-5-5` | `high` | 같음 |
| coding·plan fallback | `codex` | `gpt-6-astra` | `xhigh` | `~/.codex/models_cache.json`(지원 effort: low~ultra), `orca agent launch --help` 예시 |
| review fallback | `codex` | `gpt-6.1-sol` | `xhigh` | `~/.codex/models_cache.json` |

`--effort`는 `--model`과 함께만 쓸 수 있습니다(`orca orchestration worker-start --help`). 모델 캐시에서는 slug와 effort 목록만 읽었고, 인증 파일은 열지 않았습니다.

## 2. 한도 초과 메시지

저장소 밖의 개인 로그는 넓게 뒤지지 않았습니다. 공식 문구를 확인하지 못했으므로 감지는 대소문자를 무시한 다음 문구로 시작하고, 운영하면서 실제 문구를 `docs/orca.md`에 보강합니다: `usage limit`, `rate limit`, `limit reached`, `quota`, `429`, `resets at`.
감지만으로는 멈추지 않습니다. 설계 §6.2대로 `worker-read` 출력에 이 문구가 **분명히** 보일 때만 `worker-stop` 후 fallback합니다.

## 3. 실패 receipt 모양

준비: 사용자 요청에 따라 vlog-me를 Orca repo로 등록했습니다(`orca repo add`, repo id `c702d524-…`). main worktree에 Orca 터미널 `orca-spike-receipt`를 만들어 coordinator로 썼습니다. Run `run_12a0988c895f`에서 Codex worker를 `--model gpt-nonexistent-spike --effort xhigh`로 한 번 띄웠습니다. 새 worktree는 만들지 않았고 파일도 바뀌지 않았습니다.

| 관찰 | 값 |
| --- | --- |
| `worker-start` 종료 코드 | 1 (JSON은 `ok: true`, `result.state: failed`) |
| 모델 사전 검증 | 없음. `launch.effective.model`에 잘못된 ID가 그대로 들어감 |
| `failedStage` | `dispatch_input` |
| `lastError` | `The dispatch preamble was not delivered (providerRejected): The agent didn't accept this message.` |
| worker 모드 | `structured`(사용자 기본 설정: chat 세션 worker) |
| transcript(`worker-read`) | Codex 경고 한 줄(`service tier priority`가 이 모델에 지원되지 않음)뿐이고, "모델 없음" 같은 명확한 오류 문구는 없음 |
| `worker-read` status | worker `failed`, terminal `exited`, liveness `exited` |
| `worker-list` projection | outcome `failed`, liveness `unverifiable`(`missing_status`), attention `failure`·`unverifiable`, nextAction `worker-release` |
| `residualResources` | agent 터미널 1개(`structworker_…`) |

정리: `worker-release`(transcript 보관 `captured`, agent 터미널 닫힘) → coordinator 터미널 탭 닫기 → `terminal list`에 남은 터미널 없음, `git worktree list`와 `git status` 변화 없음. Run과 Task(`task_5772a414c70a`, `failed`)는 Orca 기록으로 남습니다. 지우는 명령은 Run 전체를 초기화하는 `orchestration reset`뿐이라 실행하지 않았습니다.

**운영에 주는 의미**
- 잘못된 모델 ID는 시작 전에 걸러지지 않습니다. `worker-start`가 0이 아닌 코드로 끝나고 `failedStage: dispatch_input`, `providerRejected`가 나오면, 먼저 모델 ID 오타나 사용 불가를 의심합니다. 이것은 한도 초과가 아니므로 fallback하지 않고 사용자에게 알립니다.
- `worker-read`의 liveness(`exited`)와 `worker-list`의 fleet liveness(`unverifiable`)는 다를 수 있습니다. 정리 여부는 `nextAction`을 따릅니다.
- 한도 초과는 이와 달리 **실행 중에** 나타날 것으로 예상합니다. 이번 실험으로는 그 문구를 확인할 수 없습니다.

## 4. setup hook 위치

- Orca는 저장소 루트의 `orca.yaml`을 읽습니다. 허용 키: `scripts`(`setup`, `archive`), `setupAgentStartupPolicy`, `issueCommand`, `defaultTabs`, `environmentRecipes`, `worktree`(Orca 번들 `orcad-server.js`의 parser).
- `worktree.sharedDirectories`: **gitignore된 디렉터리만** 새 worktree에 symlink로 공유합니다. 상대 경로만 받고 `..`, `.git`, 절대 경로는 거부합니다.
- 그래서 계획의 `scripts/orca-setup.sh` 대신 `orca.yaml`의 `sharedDirectories: [.tools, renderer/node_modules]`를 씁니다(Claude 판단, 계획 Task 6 변경). 스크립트를 따로 유지할 필요가 없습니다.
- vlog-me는 2026-10-22 사용자 요청으로 Orca repo에 등록했습니다. `orca.yaml` 신뢰 승인은 사용자가 Orca에서 합니다(이번 실험은 기존 worktree를 써서 hook이 실행되지 않았습니다. `hookFound: false`).

## 5. worktree에서 검증

임시 git worktree(`--detach`, scratchpad 아래)에 `.tools`와 `renderer/node_modules`를 symlink하고 실행했습니다. 확인 뒤 worktree를 제거했습니다(`git worktree list`에 남지 않음).

| 검사 | 결과 | 이유 |
| --- | --- | --- |
| `./init.sh` 전체 | FAIL(예상) | doctor가 원본 없는 환경을 거부 |
| doctor `scope` | FAIL | live `config/project.json`의 `source_roots`가 worktree에 없음 |
| doctor `audio_library` | FAIL | `assets/audio/`가 worktree에 없음(미디어라 공유하지 않음) |
| doctor `local_browser` | FAIL | `safe_path`가 symlink 경로를 거부(`node_modules`가 symlink) |
| Python 테스트 152개 | 151 PASS, 1 ERROR, 6 skip | ERROR는 `test_phase_configs.LiveConfigTests`(live 설정의 원본 폴더 확인) |
| compileall·lint·typecheck·node test | PASS | |

**결론(Claude 판단):** worker는 원본과 음원이 없는 worktree에서 일하므로 doctor와 live-config 테스트는 원래 통과할 수 없습니다. 이것은 격리가 동작한다는 뜻이기도 합니다. 그래서 다음과 같이 나눕니다.
- worker와 coordinator의 worktree 검증: 새 `scripts/dev-check.sh`. doctor를 빼고, live-config 테스트만 제외한 Python 테스트, compileall, lint, typecheck, node test를 실행합니다.
- 전체 `./init.sh`: 사용자가 병합을 승인한 뒤 main checkout에서 coordinator가 실행합니다. FAIL이면 사용자에게 알리고 되돌릴지 묻습니다.
