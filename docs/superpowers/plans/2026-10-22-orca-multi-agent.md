# Orca 멀티 에이전트 개발 구조 구현 계획

- 날짜: 2026-10-22
- 설계: [2026-10-22-orca-multi-agent-design.md](../specs/2026-10-22-orca-multi-agent-design.md) (2026-10-22 사용자 승인)
- 실행 방식: 현재 규칙대로 **Claude 단일 세션**에서 진행합니다. Orca worker, Codex, subagent는 쓰지 않습니다(설계 §9).
- feature id: `orca-dev-orchestration`

## 원칙

- 한 번에 한 task씩 진행하고, task마다 검증 결과(PASS/FAIL/NOT_RUN/BLOCKED)를 기록합니다.
- `config/project.json`, `config/*.example.json`, `scripts/production.py`, `scripts/common.py`는 건드리지 않습니다.
- `sources/`, `work/`, `raw/`, `assets/audio/`, `.env*`는 읽지 않습니다.
- 커밋, push, 실제 Orca Run 생성은 사용자가 요청할 때만 합니다. 이 계획 안의 Orca 명령은 `--help`와 읽기 전용 조회, 그리고 Task 1처럼 사용자가 허락한 짧은 확인만 실행합니다.
- 각 task가 끝나면 `./init.sh`를 실행해 기존 검증이 깨지지 않았는지 확인합니다.

## Task 0. feature 등록

**파일:** `feature_list.json`, `progress.md`

1. `first-real-sample`의 `status`를 `on_hold`로 바꾸고 `evidence`에 "2026-10-22 orca-dev-orchestration 작업 동안 보류"를 덧붙입니다.
2. 새 feature를 추가합니다.
   - `id`: `orca-dev-orchestration`
   - `status`: `in_progress`
   - `dependencies`: `["phase-aware-harness"]`
   - `done_criteria`: 문서 분리, `AGENTS.md`, 운영 문서, 지시문 템플릿, setup 스크립트, 테스트, spike 결과 기록, `./init.sh` PASS.
3. `progress.md`에 시작 기록을 한 줄 추가합니다.

**검증:** `./init.sh` PASS. JSON 문법 오류가 없는지 확인합니다.

## Task 1. 사전 확인(spike)

설계 §10의 확인 항목입니다. 결과에 따라 Task 4~6의 세부 내용이 바뀌므로 먼저 합니다. 결과는 `reports/orca-spike-2026-10-22.md`에 기록합니다.

1. **모델 ID와 effort 값:** `orca orchestration worker-start --help`, `orca agent launch --help`, Codex 설정(`~/.codex/config.toml`이 있으면 모델 키 이름만 확인, 비밀 값은 출력하지 않음)으로 opus 5.5, sonnet 5.5, astra 6, sol 6.1의 provider 모델 ID와 effort 표기(`medium`, `high`, `xhigh`)를 확인합니다. 확인되지 않은 ID는 템플릿에서 `<확인 필요>`로 남깁니다.
2. **한도 초과 메시지 형식:** 이 저장소 범위 밖의 개인 로그를 넓게 뒤지지 않습니다. Claude Code와 Codex 공식 문서나 CLI 도움말에서 rate limit·usage limit 메시지 문구를 확인합니다. 찾지 못하면 "확인 안 됨"으로 기록하고, 감지 문구 목록은 운영하면서 보강하도록 남깁니다.
3. **실패 receipt 모양:** 사용자에게 한 번 확인받은 뒤, 존재하지 않는 모델 ID로 worker를 1회 띄워 실패 receipt의 `failedStage`, outcome, liveness 필드를 기록합니다. 사용자가 원하지 않으면 NOT_RUN으로 남깁니다. 실행했다면 생성된 Run, worktree, 터미널을 정리하고 그 결과도 기록합니다.
4. **setup hook 위치:** Orca가 repo setup hook을 어디서 읽는지(앱 설정인지 저장소 파일인지) `orca` 도움말과 `orca skills get orca-cli --full`에서 확인합니다.
5. **worktree에서 init.sh:** 임시 git worktree를 `/private/tmp` 아래에 만들고, `.tools/`와 `renderer/node_modules`를 symlink한 뒤 `./init.sh`를 실행합니다. 확인이 끝나면 worktree를 제거합니다(`git worktree remove`). 이 단계는 Orca 없이 git만으로 합니다.

**검증:** 보고서에 항목별 결과와 근거가 있고, 임시 worktree와 Orca 리소스가 남아 있지 않습니다(`git worktree list`).

## Task 2. 규칙 범위 분리

**파일:** `CLAUDE.md`, `docs/workflow.md`

1. `CLAUDE.md` 18행 "Claude Code is the only production agent interface. No Codex handoff…"를 두 문장으로 나눕니다.
   - production 작업(실제 미디어, `prod-*` run, 렌더)은 지금처럼 Claude Code 단일 세션으로만 합니다.
   - 개발 작업(`scripts/`, `renderer/`, `tests/`, `docs/`, 하네스 파일)은 `docs/orca.md`의 Orca 흐름을 쓸 수 있습니다. 한 Run 안에서 두 작업을 섞지 않습니다.
2. `docs/workflow.md` 9행의 "subagent나 외부 coordinator는 쓰지 않습니다"를 "production 흐름에서는"으로 한정하고 `docs/orca.md`로 연결합니다.
3. `use_subagents` 설정과 검증은 그대로라는 점을 `docs/orca.md`에 적습니다(Task 4).

**검증:** `./init.sh` PASS. `grep -n "subagent\|Codex" CLAUDE.md docs/workflow.md`로 남은 문구가 서로 모순되지 않는지 확인합니다.

## Task 3. `AGENTS.md` 작성

**파일:** `AGENTS.md`(신규, 저장소 루트)

설계 §5.2의 내용을 Codex가 바로 따를 수 있게 짧게 씁니다.
- 역할: Orca coding worker. 받은 plan 문서의 범위만 구현합니다.
- 금지: `sources/`·`work/`·`raw/`·`assets/audio/`·`.env*` 접근(절대 경로 포함), push, main 병합, `feature_list.json`·`progress.md`·`session-handoff.md`·`reports/` 수정, 테스트 기대값 약화, 다운로드, 렌더, 외부 호출, `config/`의 phase·권한 값 변경.
- 허용: worker 브랜치(Orca 기본 `<git 사용자>/<name>`)에 로컬 커밋.
- 검증 명령: `./init.sh`, 관련 `python3 -m unittest tests.<모듈>`, `npm --prefix renderer run lint|typecheck|test`(`./scripts/npm.sh` 경유).
- 완료 보고: 변경 파일, 실행한 검증과 결과, 남은 문제.
- Skill 파일을 바꾸면 `config/skills-lock.json` hash도 갱신해야 한다는 점.

**검증:** Task 7의 테스트가 핵심 금지 문구 존재를 확인합니다.

## Task 4. 운영 문서 `docs/orca.md`

**파일:** `docs/orca.md`(신규)

설계 §1·§5·§6·§7을 사용자와 coordinator가 그대로 따라 할 수 있는 절차로 옮깁니다.
1. 역할·모델 표(Task 1에서 확인한 ID 반영).
2. 시작 전 확인: main이 깨끗한지, production 세션이 진행 중이 아닌지.
3. 기본 흐름 1~9단계와 단계별 `orca` 명령 예시(`run-create`, `worker-start --worktree new-child --agent codex --model … --effort xhigh`, `check --wait`, `worker-release`).
4. 리뷰 조건 7개와 판정 방법. diff 줄 수는 `git diff --numstat main...<branch>`의 추가+삭제 합계로 계산하고, `package-lock.json` 같은 생성 파일은 뺍니다.
5. fallback 절차: 감지 문구(Task 1 결과), `worker-read`로 확인, `worker-stop`, `--retry-of` 재실행, 상태 파일 기록.
6. coordinator 이어받기 절차: 사용자가 Codex 세션을 열고 줄 첫 지시문(Task 5 템플릿), `run-use`로 같은 Run에 붙기.
7. 병합 절차: 병합 전 확인 항목(검증 결과, 리뷰, `sources/`·`work/` 경로 언급 검사, main 미커밋 변경 없음), 사용자 승인 뒤 `git merge --no-ff <branch>`, push 금지.
8. 상태 파일 형식과 위치: `.orca-runs/<run-id>.md`(gitignore 대상, `work/`와 분리).
9. 정리: worker release, worktree 삭제는 사용자 확인 후.

**검증:** 문서 안의 모든 파일 경로와 명령이 실제로 존재하는지 확인합니다(`orca … --help`로 플래그 확인).

## Task 5. 지시문 템플릿

**파일:** `docs/orca/plan-worker.md`, `docs/orca/coding-worker.md`, `docs/orca/review-worker.md`, `docs/orca/coordinator-takeover.md`(모두 신규)

- 공통: 개발 작업만 한다는 범위, 금지 경로, 완료 보고 형식, `worker_done`의 `--outcome` 사용.
- plan worker: 결과를 `docs/superpowers/plans/<날짜>-<기능>.md`에 쓰고 코드는 바꾸지 않습니다.
- coding worker: `AGENTS.md`와 plan 문서 경로를 읽고 시작합니다.
- review worker: plan 문서와 `git diff main...<branch>`만 받습니다. coding 대화는 받지 않습니다. 결과는 심각도 순 목록과 "병합 가능/수정 필요" 판정입니다. 코드는 바꾸지 않습니다.
- coordinator 이어받기: 상태 파일 경로를 받아 `docs/orca.md`의 절차를 따르고, plan·review에는 fallback 모델을 바로 쓰도록 합니다.

**검증:** 각 템플릿에 금지 경로와 완료 보고 형식이 들어 있는지 Task 7 테스트로 확인합니다.

## Task 6. worktree 설정과 개발용 검증 스크립트

> 2026-10-22 변경: Task 1에서 Orca가 `orca.yaml`의 `worktree.sharedDirectories`로 gitignore된 디렉터리를 worktree에 symlink하는 기능을 기본 제공한다는 것을 확인했습니다. 또 원본이 없는 worktree에서는 doctor와 live-config 테스트가 통과할 수 없다는 것도 확인했습니다([spike 보고서](../../../reports/orca-spike-2026-10-22.md)). 그래서 setup 스크립트 대신 아래처럼 바꿉니다.

**파일:** `orca.yaml`(신규), `scripts/dev-check.sh`(신규), `scripts/dev_tests.py`(신규), `.gitignore`

1. `orca.yaml`: `worktree.sharedDirectories: [.tools, renderer/node_modules]`. `sources`, `work`, `assets`, `raw`는 넣지 않습니다. `scripts.setup`은 두지 않습니다.
2. `scripts/dev_tests.py`: `tests/`를 discover하되 live 설정을 읽는 `test_phase_configs.LiveConfigTests`만 빼고 실행합니다.
3. `scripts/dev-check.sh`: `scripts/env.sh`를 불러온 뒤 `dev_tests.py`, compileall, renderer lint·typecheck·test를 실행합니다. doctor는 실행하지 않습니다. worker와 coordinator가 worktree에서 씁니다.
4. 전체 `./init.sh`는 사용자가 병합을 승인한 뒤 main checkout에서 coordinator가 실행합니다.
5. `.gitignore`에 `.orca-runs/`를 추가합니다.

**검증:** 임시 git worktree에서 `scripts/dev-check.sh` PASS. main에서 `./init.sh` PASS.

## Task 7. 테스트

**파일:** `tests/test_orca_harness.py`(신규)

`tests/test_startup.py`처럼 `unittest`와 임시 디렉터리(`/private/tmp`)를 씁니다. 실제 `config/project.json`은 읽지 않습니다.
1. `AGENTS.md`에 핵심 금지 경로(`sources/`, `work/`, `.env`)와 push·merge 금지 문구가 있습니다.
2. `CLAUDE.md`와 `docs/workflow.md`가 production 작업의 subagent 금지를 유지합니다(문구 존재 확인).
3. `config/setup.example.json`과 `config/production.example.json`의 `use_subagents`가 여전히 `false`입니다.
4. `docs/orca/` 템플릿 네 개가 있고, 각각 금지 경로를 언급합니다.
5. `orca.yaml`의 `sharedDirectories`에 `.tools`와 `renderer/node_modules`만 있고, `sources`·`work`·`assets`·`raw`가 없습니다. `scripts/dev_tests.py`는 `LiveConfigTests`만 제외합니다.
6. `.gitignore`에 `.orca-runs/`가 있습니다.

**검증:** `python3 -m unittest tests.test_orca_harness -v` PASS, `./init.sh` PASS.

## Task 8. 마무리 기록

**파일:** `feature_list.json`, `progress.md`, `session-handoff.md`, `reports/README.md`, `reports/orca-dev-orchestration.md`(신규)

1. 보고서에 task별 PASS/FAIL/NOT_RUN/BLOCKED와 근거를 적습니다.
2. 남은 한계를 적습니다. 실제 한도 초과 상황의 자동 fallback은 운영 중에야 검증됩니다. 격리는 OS 수준이 아닙니다. 모델 ID 중 확인되지 않은 것이 있으면 그 목록도 적습니다.
3. `orca-dev-orchestration`을 `completed`로 바꾸고, `first-real-sample`을 다시 `in_progress`로 돌릴지는 사용자에게 묻습니다.
4. `session-handoff.md`에 다음 허용 행동을 적습니다: 첫 실제 Orca Run은 사용자가 기능을 지정해 요청할 때 시작.

**검증:** `./init.sh` PASS. `git status`로 변경 파일이 이 계획의 파일 목록과 일치하는지 확인합니다.

## 첫 실제 사용(이 계획 범위 밖)

구현이 끝나면 작은 개발 task 하나로 실제 Orca Run을 돌려 보길 권합니다. 이때 coordinator가 이 문서의 흐름대로 plan → coding → 검증 → (조건부) 리뷰 → 병합 승인까지 가는지 확인합니다. 시작은 사용자가 요청할 때 합니다.
