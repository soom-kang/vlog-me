# Orca 멀티 에이전트 개발 구조 설계

- 날짜: 2026-10-22
- 상태: 설계 완료, 사용자 승인 대기
- 범위: vlog-me **코드 개발 작업**만 해당합니다. 영상 편집과 production run은 대상이 아닙니다.

## 1. 의도와 배경

vlog-me 개발을 Orca IDE에서 여러 에이전트에게 나눠 맡깁니다. 계획과 지휘는 Claude가, 코딩은 Codex가 하고, 필요할 때만 Claude가 독립 리뷰를 합니다. 모델별 강점을 살리는 것이 목적입니다.

Claude 사용량 한도(토큰)가 바닥나도 개발이 멈추지 않도록 Codex 계열 모델로 넘어가는 fallback을 둡니다. fallback의 기준은 **토큰 부족이나 사용량 한도 초과**입니다. 결과 품질이 부족하다는 이유로는 전환하지 않습니다.

### 모델 배정(사용자 결정)

| 역할 | 기본 | fallback |
| --- | --- | --- |
| orchestration(coordinator) | Claude opus 5.5, effort medium | 없음. coordinator가 멈추면 §6.3 수동 이어받기 |
| plan | Claude opus 5.5, effort medium | Codex astra 6, effort xhigh |
| coding | Codex astra 6, effort xhigh | 없음 |
| 독립 review | Claude sonnet 5.5, effort high | Codex sol 6.1, effort xhigh |

## 2. 목표, 비목표, 반목표

**목표**
- 개발 작업이 plan → coding → (조건부) review → 사용자 승인 → main 병합 흐름으로 진행됩니다.
- plan이나 review worker가 Claude 한도에 걸리면 coordinator가 지정된 Codex 모델로 자동 재실행합니다.
- coordinator까지 멈춰도 상태 파일을 읽은 Codex coordinator가 이어받을 수 있습니다.
- Codex는 원본 영상(`sources/`)이 없는 worktree에서 작업합니다. 이것은 OS 수준 격리가 아니라 겹겹의 방어입니다(§5.2).

**비목표**
- production run(`/vlog-workflow`, 후보, 자막, 사운드, 렌더)을 Orca나 Codex로 옮기는 것. 지금처럼 Claude 주 세션 하나가 진행합니다.
- 품질을 기준으로 모델을 자동 교체하는 것.
- coding 단계의 fallback.

**반목표(이렇게 되면 동작해도 실패로 봅니다)**
- Codex나 worker가 `sources/`, `work/`의 실제 미디어를 읽거나 쓰는 것.
- 사용자 승인 없이 main에 병합하거나, 어디로든 push하는 것.
- production 단계의 subagent 금지(`use_subagents: false`와 그 검증)가 느슨해지는 것.
- `feature_list.json`, `progress.md`, `session-handoff.md`를 여러 에이전트가 동시에 고쳐 상태가 갈라지는 것.
- 테스트를 통과시키려고 Codex가 테스트 기대값을 약하게 바꾸고, 그 변경이 리뷰 없이 지나가는 것.

## 3. 제약

- `CLAUDE.md:18`과 `docs/workflow.md:9`는 현재 "Codex handoff, subagent, 외부 coordinator를 쓰지 않는다"고 정합니다. 이 규칙을 **production 작업**에만 적용하고, **개발 작업**에는 이 설계를 허용하도록 범위를 나눠야 합니다.
- `config/project.json`의 `use_subagents: false`와 `scripts/production.py`·`scripts/common.py`의 검증은 production run 실행 계약입니다. 이 설계는 이 값과 검증을 **바꾸지 않습니다.** Orca worker는 production run을 실행하지 않기 때문입니다.
- `.claude/settings.json`의 deny 규칙과 `.claude/hooks/protect_sources.py`는 Claude Code에만 적용됩니다. Codex는 이를 읽지 않습니다.
- `sources/`, `work/`, `raw/`, `assets/audio/`, `.env*`는 `.gitignore`에 있습니다. 그래서 git worktree에는 포함되지 않습니다.
- `config/project.json`은 git에 포함되어 있고, 현재 `phase: production`입니다. worktree에도 이 설정이 그대로 들어갑니다.
- CLAUDE.md는 요청 없는 커밋과 push를 금지합니다.
- Skill 파일은 `config/skills-lock.json`으로 hash가 잠겨 있습니다.
- Orca는 자동 fallback 기능이 없습니다. `orca orchestration worker-start`는 `--agent`, `--model`, `--effort`, `--retry-of`를 지원하므로, fallback은 coordinator가 직접 판단해 재실행해야 합니다.

## 4. 검토한 방식

| 방식 | 내용 | 장단점 |
| --- | --- | --- |
| A. 상태 파일 기반 수동 전환 | 단계와 진행 상태를 파일로 남기고, Claude가 멈추면 사용자가 Codex coordinator를 띄워 이어받습니다. | 단순하고 어떤 한도 상황에서도 동작합니다. 대신 전환할 때마다 사용자가 개입해야 합니다. |
| **B. Claude coordinator + 역할별 Orca worker + A를 안전망으로 (선택)** | coordinator는 지휘만 하고, plan·coding·review는 각각 supervised worker가 맡습니다. worker가 한도 초과로 실패하면 coordinator가 `--retry-of`로 fallback 모델을 붙여 재실행합니다. coordinator 자신이 멈추면 A로 이어받습니다. | 흔한 경우(무거운 plan·review에서 한도 초과)는 자동으로 넘어가고, 최악의 경우도 대응합니다. 구성 요소가 가장 많고, 한도 초과가 Orca에서 어떻게 보이는지 확인이 필요합니다. |
| C. 스크립트가 coordinator 역할 | 셸 스크립트나 Orca automation이 단계를 돌리고 오류 메시지로 모델을 고릅니다. | LLM coordinator의 한도 문제는 없어집니다. 하지만 작업을 쪼개고 판단하는 능력을 잃고, 만들고 유지하는 비용이 이 프로젝트 규모에 비해 큽니다. |

**B를 고른 이유(사용자 결정):** coordinator는 medium effort로 지휘만 하므로 토큰을 적게 씁니다. 실제로 한도에 먼저 걸리는 쪽은 plan과 review worker일 가능성이 큽니다. 그 경우를 자동으로 처리하고, 드문 최악의 경우만 A로 받는 것이 비용 대비 효과가 가장 좋습니다.

## 5. 역할과 작업 위치

### 5.1 적용 범위 분리
- **production 작업**(실제 미디어, `prod-*` run, 렌더): 지금 규칙 그대로입니다. Claude 주 세션 하나가 진행하고 subagent와 Codex는 쓰지 않습니다.
- **개발 작업**(`scripts/`, `renderer/`, `tests/`, `docs/`, 하네스 파일 수정): 이 설계의 Orca 흐름을 씁니다.
- 한 Orca Run 안에서 두 작업을 섞지 않습니다. 개발 중 실제 미디어 확인이 필요하면 Run을 마치고 production 세션에서 따로 합니다.

### 5.2 Codex 격리
- coding worker는 항상 **새 child worktree**(`--worktree new-child`)에서 작업합니다. 브랜치 이름은 Orca 기본값 `<git 사용자>/<name>`입니다(예: `soom-kang/orca-<task>`, 2026-10-22 확인 후 수정). 이 worktree에는 `sources/`, `work/`가 없습니다.
- 저장소 루트에 Codex용 `AGENTS.md`를 새로 만듭니다. 내용은 다음과 같습니다.
  - 개발 작업만 한다는 범위, 그리고 `sources/`·`work/`·`raw/`·`assets/audio/`·`.env*`에 접근하지 않는다는 금지 사항.
  - 실행할 검증 명령(`./init.sh`, 관련 `python3 -m pytest tests/...`, renderer 타입 검사·lint).
  - 금지 사항: push, main 병합, `feature_list.json`·`progress.md`·`session-handoff.md` 수정, 테스트 기대값을 약하게 바꾸기, 다운로드, 렌더, 외부 호출.
  - worker 브랜치에 하는 로컬 커밋은 허용합니다.
- Codex 실행 시 sandbox는 worktree 쓰기만 허용하는 모드로 둡니다. 구체적인 Codex 설정 키는 구현할 때 확인합니다(§10).
- **격리 수준(Claude 판단):** Codex sandbox는 보통 쓰기만 제한하고 읽기는 막지 않습니다. 그래서 절대 경로로 main checkout의 `sources/`를 읽는 것을 기술적으로 완전히 막지는 못합니다. 이 설계는 CLAUDE.md의 원칙("permission과 helper 검사는 OS sandbox가 아니라 겹겹의 방어")을 따릅니다. 방어는 다음 세 겹입니다. (1) worktree에 `sources/`가 없음, (2) `AGENTS.md` 금지 규칙, (3) coordinator가 병합 전에 diff와 worker transcript에서 `sources/`·`work/` 경로 언급을 확인. OS 수준 격리(별도 사용자, 별도 clone이나 호스트)는 하지 않습니다.
- plan·review worker도 child worktree(또는 coordinator worktree)에서 **읽기 전용 역할**로 실행하고, 같은 금지 규칙을 지시문에 넣습니다. Claude worker에게는 worktree에 포함된 `.claude/settings.json`과 hook이 그대로 적용됩니다.
- **툴체인(Claude 판단):** `.tools/`와 `renderer/node_modules`는 gitignore 대상이라 새 worktree에 없습니다. Orca setup hook이 main checkout의 두 디렉터리를 worktree에 symlink합니다. 미디어가 아니므로 격리 원칙에 어긋나지 않고, 다운로드도 필요 없습니다. 그래서 `./init.sh` 전체 검증을 worktree 안에서 실행할 수 있습니다.

### 5.3 상태 관리 책임
- `feature_list.json`, `progress.md`, `session-handoff.md`, `reports/`와 Orca 상태 파일은 **coordinator만** 수정합니다.
- worker는 결과를 `worker_done` 요약과 `--report-path`로 전달합니다.

## 6. 흐름

### 6.1 기본 흐름
1. **시작 전 확인(coordinator):** main에 커밋되지 않은 변경이 있으면 멈추고 사용자에게 알립니다. worktree는 커밋된 시점을 기준으로 만들어지므로, 미커밋 변경은 worker에게 보이지 않습니다. 정리 방법(커밋 여부)은 사용자가 정합니다.
2. **Run 생성:** `orca orchestration run-create --objective "<기능>"`. 상태 파일을 만듭니다(§6.4).
3. **plan:** plan worker(opus 5.5 medium)를 띄웁니다. 결과는 `docs/superpowers/plans/` 아래 plan 문서입니다. coordinator가 이를 사용자에게 보여주고 승인을 받습니다.
4. **coding:** coding worker(Codex astra 6 xhigh)를 child worktree에서 띄웁니다. plan 문서 경로와 `AGENTS.md`를 지시문에 포함합니다. 독립된 작업이 여럿이면 병렬로 띄워도 되지만, 같은 파일을 두 worker가 고치지 않게 합니다.
5. **검증(coordinator):** worker 브랜치에서 `./init.sh`와 관련 테스트를 실행하고 PASS/FAIL/NOT_RUN을 기록합니다.
6. **리뷰 판단:** §7 조건 중 하나라도 해당하면 review worker(sonnet 5.5 high)를 띄웁니다. review worker는 plan과 diff만 받고, coding 과정의 대화는 받지 않습니다(독립성).
7. **리뷰 결과 처리:** 수정할 점이 있으면 coding worker에게 다시 맡깁니다. 리뷰-수정 반복은 최대 2회이고, 그 뒤에도 남으면 사용자에게 판단을 요청합니다.
8. **병합 승인:** 병합 직전에 main checkout에 커밋되지 않은 변경이 있으면 병합하지 않고 사용자에게 알립니다. production 세션이 작업 중일 수 있기 때문입니다(Claude 판단). coordinator가 검증 결과, 리뷰 결과(또는 건너뛴 이유), 변경 파일 목록을 사용자에게 보여줍니다. 사용자가 승인하면 main에 병합합니다. push는 하지 않습니다.
9. **마무리:** coordinator가 `feature_list.json`, `progress.md`, `session-handoff.md`를 갱신하고, worker 터미널을 release합니다. worktree 삭제는 사용자에게 확인한 뒤 합니다.

### 6.2 worker 단계 fallback(자동)
- 대상은 plan과 review worker뿐입니다.
- worker가 `--outcome failed`로 끝났거나 Orca가 `exited`로 판정했고, 그 출력이나 transcript에서 사용량 한도 초과 신호가 확인되면 fallback합니다.
- fallback은 `worker-start --task <같은 task> --retry-of <실패한 dispatch> --agent codex --model <fallback 모델> --effort xhigh`로 실행합니다.
- 한도 초과가 아닌 실패(코드 오류, 잘못된 지시)는 fallback하지 않습니다. coordinator가 원인을 보고 사용자에게 알립니다.
- fallback이 일어나면 상태 파일과 최종 보고에 "어떤 단계가 어떤 모델로 넘어갔는지"를 적습니다.
- **살아 있는 채 멈춘 worker(사용자 결정, 2026-10-22):** Claude Code는 한도에 걸리면 종료하지 않고 기다리는 경우가 많습니다. `worker-read` 출력에 사용량 한도 초과 메시지가 **분명히** 보이면, coordinator가 `worker-stop`으로 그 dispatch를 멈추고 위와 같이 `--retry-of`로 재실행합니다. 멈춘 근거(출력 발췌)를 상태 파일에 남깁니다.
- 한도 메시지 없이 응답만 없는 worker는 한도 초과로 추정해 멈추지 않습니다. Orca orchestration 규칙대로 기다리거나 사용자에게 알립니다.

### 6.3 coordinator 단계 이어받기(수동)
- coordinator, plan, review가 같은 Claude 계정 한도를 나눠 쓰므로, 이 경로가 생각보다 자주 쓰일 수 있습니다. 그래서 구현 순서는 상태 파일과 §6.3 이어받기를 먼저 만들고, §6.2 자동 감지는 그다음에 붙입니다(Claude 판단).
- Claude coordinator가 한도에 걸려 멈추면, 사용자가 Orca에서 Codex 세션을 coordinator로 띄웁니다.
- Codex coordinator는 상태 파일을 읽고, `orca orchestration run-use`로 같은 Run에 붙어 다음 단계부터 이어갑니다.
- 이때 plan과 review가 필요하면 fallback 모델(astra 6, sol 6.1)을 바로 씁니다.
- 이어받기 절차는 운영 문서(§8)에 사용자가 그대로 따라 할 수 있게 적습니다.

### 6.4 상태 파일
- 위치: Run마다 하나, 커밋하지 않는 경로에 둡니다. 구체 경로는 builder가 정하되, `work/`(production run 영역)와 섞이지 않게 합니다.
- 최소 내용: Run ID, 기능 이름, plan 문서 경로, 승인 여부, 각 단계의 상태(pending/running/succeeded/failed), task·dispatch ID, worker 브랜치, 사용한 모델과 fallback 여부, 검증 결과, 리뷰 실행 여부와 이유, 다음에 할 일.
- coordinator는 단계가 바뀔 때마다 이 파일을 먼저 갱신합니다. 갑자기 멈춰도 이어받을 수 있게 하기 위해서입니다.

## 7. 독립 리뷰를 돌리는 조건(사용자 결정)

하나라도 해당하면 리뷰를 돌립니다.
1. 안전 경계 코드 변경: `scripts/production.py`, `scripts/common.py`, `.claude/hooks/`, `.claude/settings.json`, `config/`.
2. 렌더 결과에 영향을 주는 변경: `scripts/render_prod.py`, `scripts/assemble.py`, `renderer/src/production/`.
3. 테스트 약화: `tests/`에서 assert나 테스트 함수가 줄어든 경우.
4. hash로 잠긴 Skill 변경: `.claude/skills/`, `config/skills-lock.json`.
5. diff가 300줄을 넘는 경우(추가+삭제, 생성 파일 제외).
6. plan이 fallback 모델로 작성된 경우.
7. 사용자가 요청한 경우.

리뷰를 건너뛰어도 §6.1의 5단계 검증은 항상 합니다. 병합 승인 요청에 "리뷰를 건너뛴 이유: 해당 조건 없음"을 적습니다.

## 8. 추가하거나 바꿀 파일

| 파일 | 변경 |
| --- | --- |
| `AGENTS.md`(신규) | Codex worker용 범위, 금지 사항, 검증 명령(§5.2). |
| `CLAUDE.md` | "No Codex handoff…" 규칙을 production 작업 한정으로 바꾸고, 개발 작업은 Orca 운영 문서를 따르도록 연결합니다. |
| `docs/workflow.md` | 9행의 subagent 금지를 production 흐름 한정으로 명시하고 운영 문서로 연결합니다. |
| `docs/orca.md`(신규, 이름은 builder 재량) | 역할·모델 표, 기본 흐름, fallback 절차, coordinator 이어받기 절차, 리뷰 조건, 상태 파일 형식, 자주 쓰는 `orca` 명령. |
| 역할별 지시문 템플릿 | plan·coding·review worker에게 넘길 `--spec` 본문. 위치는 builder 재량(예: `docs/orca/` 아래). |
| `.gitignore` | 상태 파일 경로가 이미 무시되지 않으면 추가합니다. |
| `tests/` | 규칙 분리 뒤에도 production의 `use_subagents: false` 검증이 그대로인지, `AGENTS.md`에 핵심 금지 사항이 있는지 확인하는 테스트(기존 `tests/test_startup.py` 방식 참고). |
| `feature_list.json`, `progress.md`, `session-handoff.md` | 이 기능을 하나의 feature로 등록하고 진행 상태를 기록합니다. |

`config/project.json`, `config/*.example.json`, `scripts/production.py`, `scripts/common.py`는 바꾸지 않습니다.

## 9. 이 기능을 만드는 방식

- 이 기능 자체는 **현재 규칙대로 Claude 단일 세션에서** 만듭니다. Orca 흐름은 이 기능이 완성되고 승인된 뒤부터 씁니다.
- 시작 시점의 main은 사용자가 이전 변경을 커밋해 깨끗한 상태입니다(커밋 `994191d`, 2026-10-22).
- `feature_list.json`에서 진행 중인 `first-real-sample`은 이 기능을 시작할 때 보류로 표시하고, 이 기능을 새 feature로 등록합니다. 진행 중인 기능은 하나만 둡니다(Claude 판단).

## 10. builder에게 맡기는 부분과 먼저 확인할 것

**구현 첫 단계에서 확인(spike)**
- Claude·Codex worker가 사용량 한도에 걸렸을 때 Orca에서 어떻게 보이는지(`failed`로 끝나는지, 멈춘 채 `live`로 남는지)와 출력 메시지 형식. 실제 한도를 일부러 채울 수는 없으므로, 존재하지 않는 모델 ID로 worker를 띄워 실패 receipt 모양을 보고, 기존 Claude·Codex 로그에서 rate limit 메시지 형식을 확인합니다. 결과에 따라 §6.2의 감지 방법을 확정합니다.
- astra 6, sol 6.1, opus 5.5, sonnet 5.5의 정확한 provider 모델 ID와 effort 값 이름이 `worker-start --model/--effort`에서 받아들여지는지.
- worktree 안에서 `./init.sh`와 테스트가 `sources/` 없이 통과하는지(현재 `phase: production` 설정 그대로).
- Codex sandbox를 worktree 쓰기 전용으로 두는 실제 설정 방법.

**builder 재량**
- 운영 문서와 지시문 템플릿의 파일 이름과 위치, 상태 파일의 정확한 경로와 형식.
- 지시문 문구, `orca` 명령 예시 구성.
- diff 줄 수 계산 방법(§7-5).
