# plan worker 지시문

`<...>`를 채워 `worker-start --spec`에 넣습니다.

```text
vlog-me 개발 작업의 구현 계획을 씁니다. 코드와 설정은 바꾸지 않습니다.

기능: <기능 이름과 사용자가 원하는 것>
참고: <설계 문서나 관련 파일 경로>

규칙:
- 개발 작업만 다룹니다. sources/, work/, raw/, assets/audio/, .env* 는 읽지 않습니다(절대 경로 포함).
- AGENTS.md와 docs/orca.md를 먼저 읽습니다. 계획은 Codex coding worker가 그대로 따를 수 있어야 합니다.
- 결과는 docs/superpowers/plans/<YYYY-MM-DD>-<기능>.md 하나에만 씁니다.
- 계획에 담을 것: 바꿀 파일, task 순서, task별 검증(./scripts/dev-check.sh와 관련 테스트), 범위 밖으로 남기는 것.
- 궁금한 점은 preamble의 ask 명령으로 coordinator에게 묻습니다.

완료 보고(worker_done, --outcome succeeded|failed):
- plan 문서 경로
- 핵심 결정과 남은 질문
```
