# Orca 개발 흐름

코드 개발 작업(`scripts/`, `renderer/`, `tests/`, `docs/`, 하네스 파일)을 Orca에서 여러 에이전트에게 나눠 맡기는 절차입니다. 영상 편집과 production run은 대상이 아닙니다. production은 지금처럼 Claude Code 단일 세션으로만 하고, `use_subagents`는 `false`로 둡니다. 설계: [2026-10-22-orca-multi-agent-design.md](superpowers/specs/2026-10-22-orca-multi-agent-design.md).

## 역할과 모델

| 역할 | `--agent` | `--model` | `--effort` | fallback(한도 초과 때) |
| --- | --- | --- | --- | --- |
| coordinator | `claude` | `claude-opus-5-5` | `medium` | 수동 이어받기(아래) |
| plan | `claude` | `claude-opus-5-5` | `medium` | `codex` · `gpt-6-astra` · `xhigh` |
| coding | `codex` | `gpt-6-astra` | `xhigh` | 없음 |
| 독립 review | `claude` | `claude-sonnet-5-5` | `high` | `codex` · `gpt-6.1-sol` · `xhigh` |

모델 ID 근거: [spike 보고서](../reports/orca-spike-2026-10-22.md). fallback은 **사용량 한도 초과**일 때만 합니다. 결과 품질이 부족하다는 이유로는 모델을 바꾸지 않습니다.

## 처음 한 번 할 일(사용자)

1. Orca에 이 저장소를 등록합니다: `orca repo add`(또는 Orca 앱에서 폴더 추가). 2026-10-22에 등록했습니다.
2. 저장소의 `orca.yaml`을 신뢰하도록 Orca에서 승인합니다. 이 파일은 새 worktree에 `.tools/`와 `renderer/node_modules`만 symlink합니다(`worktree.sharedDirectories`). 원본 미디어와 음원 폴더는 공유하지 않습니다.
3. coordinator로 쓸 Claude 세션을 Orca의 vlog-me main worktree에서 엽니다(모델 opus 5.5, effort medium).

## 작업 요청 방법

Orca에서 연 Claude 세션에는 **작업 내용만** 적으면 됩니다. 예: `review 카드에 후보 길이 합계를 표시해줘`.
`CLAUDE.md`의 "Orca Development Sessions" 규칙에 따라 Claude가 역할을 스스로 정합니다.
- Orca 세션이고(`orca status --json`의 `caller.orcaSessionId`) 개발 작업이면, coordinator로서 아래 흐름 전체를 진행합니다.
- dispatch preamble이 있는 세션은 worker로만 일합니다.
- Orca 밖이거나 production·미디어 작업이면, 지금처럼 단일 Claude 세션으로 일합니다.

사용자 승인은 그대로 두 번입니다: plan 문서 승인, main 병합 승인.

## 시작 전 확인(coordinator)

- main checkout에 커밋되지 않은 변경이 없어야 합니다. worktree는 커밋된 시점에서 만들어지므로, 미커밋 변경은 worker에게 보이지 않습니다. 있으면 멈추고 사용자에게 알립니다.
- production 세션이 진행 중이 아니어야 합니다. 확실하지 않으면 사용자에게 묻습니다.
- `feature_list.json`에서 이 작업을 진행 중인 feature로 등록합니다(진행 중은 하나만).

## 기본 흐름

명령의 `<...>`는 receipt(`--json` 출력)에서 받은 실제 값으로 바꿉니다. 단계가 바뀔 때마다 **먼저** 상태 파일을 갱신합니다.

1. **Run 생성**
   ```text
   orca status --json
   orca orchestration run-create --objective "<기능 이름>" --json
   ```
   상태 파일 `.orca-runs/<run-id>.md`를 만듭니다(형식은 아래).
2. **plan** — [plan worker 지시문](orca/plan-worker.md)을 채워 띄웁니다.
   ```text
   orca orchestration worker-start --spec "<지시문>" --worktree current --agent claude --model claude-opus-5-5 --effort medium --json
   ```
   결과 plan 문서(`docs/superpowers/plans/<날짜>-<기능>.md`)를 사용자에게 보여주고 승인을 받습니다.
3. **coding** — [coding worker 지시문](orca/coding-worker.md)을 채워 child worktree에서 띄웁니다.
   ```text
   orca orchestration worker-start --spec "<지시문>" --worktree new-child --name orca-<task> --agent codex --model gpt-6-astra --effort xhigh --json
   ```
   Orca는 worker 브랜치를 `<git 사용자>/<name>` 형식으로 만듭니다(예: `soom-kang/orca-<task>`). 아래 `<branch>`는 receipt의 worktree 정보나 worktree에서 `git branch --show-current`로 확인한 실제 이름입니다. 상태 파일에도 적습니다.
   독립된 작업이 여럿이면 병렬로 띄워도 됩니다. 다만 같은 파일을 두 worker가 고치지 않게 합니다.
4. **대기**
   ```text
   orca orchestration check --wait --types "worker_done,escalation,question" --timeout-ms 900000 --json
   ```
   질문에는 `orchestration reply`로 답합니다. 메시지를 처리한 뒤 `--ack <delivery_id>`로 확인합니다.
5. **검증** — worker의 worktree에서 `./scripts/dev-check.sh`를 실행하고 PASS/FAIL을 기록합니다. worktree에서는 `./init.sh`를 쓰지 않습니다. doctor와 live-config 테스트는 원본 미디어가 있어야 통과하기 때문입니다.
6. **리뷰 판단** — 아래 조건 중 하나라도 해당하면 [review worker 지시문](orca/review-worker.md)으로 독립 리뷰를 띄웁니다.
   ```text
   orca orchestration worker-start --spec "<지시문>" --worktree current --agent claude --model claude-sonnet-5-5 --effort high --json
   ```
   review worker에게는 plan 문서와 diff만 줍니다. coding 대화는 주지 않습니다.
7. **수정 반복** — 리뷰에서 고칠 점이 나오면 coding worker에게 다시 맡깁니다. 이 반복은 최대 2회입니다. 그래도 남은 문제는 사용자에게 판단을 요청합니다.
8. **병합 승인** — 아래 "병합" 절차를 따릅니다.
9. **정리** — `orca orchestration worker-release --dispatch <id> --json`. worktree 삭제는 사용자 확인 뒤에 합니다. `feature_list.json`, `progress.md`, `session-handoff.md`는 coordinator만 갱신합니다.

## 독립 리뷰 조건

하나라도 해당하면 리뷰를 돌립니다. 해당하지 않으면 병합 승인 요청에 "리뷰 생략: 해당 조건 없음"이라고 적습니다.

1. 안전 경계 코드: `scripts/production.py`, `scripts/common.py`, `.claude/hooks/`, `.claude/settings.json`, `config/`, `AGENTS.md`, `orca.yaml`.
2. 렌더 결과에 영향: `scripts/render_prod.py`, `scripts/assemble.py`, `renderer/src/production/`.
3. 테스트 약화: `tests/`에서 assert나 테스트 함수가 줄어든 경우(`git diff main...<branch> -- tests/`에서 삭제된 `assert`·`def test_` 줄 확인).
4. hash로 잠긴 Skill: `.claude/skills/`, `config/skills-lock.json`.
5. diff가 300줄 초과: `git diff --numstat main...<branch>`의 추가+삭제 합계. `package-lock.json` 같은 생성 파일은 뺍니다.
6. plan을 fallback 모델이 썼을 때.
7. 사용자가 요청했을 때.

## 한도 초과 fallback

대상은 plan과 review worker뿐입니다.

1. worker가 `failed`로 끝났거나 멈춘 것처럼 보이면 출력을 읽습니다.
   ```text
   orca orchestration worker-read --dispatch <id> --json
   ```
2. 출력에 사용량 한도 초과 메시지가 **분명히** 있을 때만 fallback합니다. 현재 감지 문구는 `usage limit`, `rate limit`, `limit reached`, `quota`, `429`, `resets at`입니다(대소문자 무시). 실제로 본 문구는 이 목록에 추가합니다.
3. worker가 아직 살아 있으면 멈춥니다. Claude Code는 한도에 걸려도 종료하지 않고 기다리는 경우가 많습니다.
   ```text
   orca orchestration worker-stop --dispatch <id> --json
   ```
4. 같은 Task를 fallback 모델로 다시 실행합니다.
   ```text
   orca orchestration worker-start --task <task_id> --retry-of <id> --worktree current --agent codex --model <gpt-6-astra|gpt-6.1-sol> --effort xhigh --json
   ```
5. 상태 파일에 근거(출력 발췌), 멈춘 dispatch, 새 dispatch, 사용한 모델을 적습니다.

`worker-start`가 시작 단계에서 바로 실패하고 receipt에 `failedStage: dispatch_input`, `providerRejected`가 있으면, 한도 초과가 아니라 모델 ID 오류나 사용 불가일 가능성이 큽니다. Orca는 모델 ID를 미리 검증하지 않습니다([spike 보고서](../reports/orca-spike-2026-10-22.md) 3번). 이 경우 fallback하지 않고 `worker-release`로 정리한 뒤 사용자에게 알립니다.

한도 메시지 없이 응답만 없는 worker는 멈추지 않습니다. 기다리거나 `worker-list --json`으로 상태를 보고, 판단이 어려우면 사용자에게 알립니다. 코드 오류나 잘못된 지시로 실패한 경우도 fallback하지 않고 사용자에게 알립니다.

## coordinator 이어받기(수동)

coordinator, plan, review는 같은 Claude 한도를 나눠 씁니다. 그래서 coordinator가 먼저 멈출 수 있습니다.

1. 사용자가 Orca에서 Codex 세션을 엽니다(`gpt-6-astra`, effort `xhigh` 권장).
2. [이어받기 지시문](orca/coordinator-takeover.md)에 상태 파일 경로를 넣어 보냅니다.
3. Codex coordinator가 `orca orchestration run-use --id <run-id> --json`으로 같은 Run에 붙어 다음 단계부터 이어갑니다. 이 Run이 끝날 때까지 plan과 review에는 fallback 모델을 바로 씁니다.

## 병합

1. 확인 항목: `dev-check.sh` 결과, 리뷰 결과(또는 생략 이유), 변경 파일 목록, diff와 worker transcript에 `sources/`·`work/`·`assets/audio/` 경로가 언급됐는지, main checkout에 미커밋 변경이 없는지.
2. 이 내용을 사용자에게 보여주고 승인을 받습니다.
3. 승인되면 main checkout에서 `git merge --no-ff <branch>`를 실행합니다. push는 하지 않습니다.
4. main에서 `./init.sh`를 실행합니다. FAIL이면 사용자에게 알리고, 되돌릴지(`git revert -m 1 <merge>`) 묻습니다.

## 상태 파일

위치는 `.orca-runs/<run-id>.md`입니다(gitignore 대상, `work/`와 분리).

```markdown
# <run-id> · <기능>
- feature: <feature id>
- plan: <plan 문서 경로> (승인: yes/no)
- 다음 할 일: <한 줄>

| 단계 | 상태 | task | dispatch | 모델 | fallback | branch/worktree |
| --- | --- | --- | --- | --- | --- | --- |
| plan | succeeded | ... | ... | claude-opus-5-5 | no | - |
| coding | running | ... | ... | gpt-6-astra | - | soom-kang/orca-<task> |
| review | pending | | | | | |

## 검증
- dev-check: PASS/FAIL (시각)
- 리뷰: 실행/생략(이유)

## 기록
- <시각> <무엇을 왜 했는지, fallback 근거 발췌>
```

## 한계

- 격리는 OS 수준이 아닙니다. worktree에 원본이 없다는 점, `AGENTS.md` 규칙, 병합 전 경로 확인이 겹겹으로 막습니다. Codex sandbox는 보통 읽기를 막지 않습니다.
- 한도 초과 메시지의 정확한 문구와 실패 receipt 모양은 실제 운영에서 확인하며 보강합니다.
