# coding worker 지시문

`<...>`를 채워 `worker-start --spec`에 넣습니다. coding worker는 항상 `--worktree new-child`로 띄웁니다.

```text
승인된 계획대로 vlog-me 코드를 구현합니다.

계획: <docs/superpowers/plans/...md 경로>
이번 범위: <계획의 task 번호나 범위>
(수정 반복이면) 리뷰 결과: <고칠 항목>

규칙:
- 시작 전에 AGENTS.md를 읽고 그대로 따릅니다.
- sources/, work/, raw/, assets/audio/, .env* 는 읽지도 쓰지도 않습니다(다른 checkout의 절대 경로 포함).
- push, main 병합 금지. 이 worktree 브랜치에 로컬 커밋만 합니다.
- feature_list.json, progress.md, session-handoff.md, reports/ 는 고치지 않습니다.
- 테스트를 약하게 바꾸지 않습니다.
- 다운로드, 설치, 렌더, 외부 호출을 하지 않습니다.
- 끝내기 전에 ./scripts/dev-check.sh 를 실행합니다.

완료 보고(worker_done, --outcome succeeded|failed):
- 변경 파일
- 실행한 검증과 PASS/FAIL
- 남은 문제나 불확실한 점
```
