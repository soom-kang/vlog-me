# coordinator 이어받기 지시문

Claude coordinator가 한도로 멈췄을 때, 사용자가 Orca에서 연 Codex 세션에 보냅니다.

```text
vlog-me Orca 개발 Run의 coordinator 역할을 이어받습니다.

상태 파일: .orca-runs/<run-id>.md

절차:
1. AGENTS.md, docs/orca.md, 상태 파일을 읽습니다.
2. orca orchestration run-use --id <run-id> --json 으로 같은 Run에 붙습니다.
3. 상태 파일의 "다음 할 일"부터 docs/orca.md의 기본 흐름대로 이어갑니다.
4. 이 Run이 끝날 때까지 plan은 gpt-6-astra(xhigh), review는 gpt-6.1-sol(xhigh)로 띄웁니다.
5. 단계가 바뀔 때마다 상태 파일을 먼저 갱신합니다.

규칙:
- sources/, work/, raw/, assets/audio/, .env* 는 읽지 않습니다(절대 경로 포함).
- main 병합은 사용자 승인 뒤에만 합니다. push는 하지 않습니다.
- 실행 중인 worker는 종료가 확인되거나 한도 초과 메시지가 분명할 때만 멈춥니다.
```
