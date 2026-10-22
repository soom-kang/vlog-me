# review worker 지시문

`<...>`를 채워 `worker-start --spec`에 넣습니다. coding 대화나 worker 요약은 넣지 않습니다(독립성).

```text
vlog-me 변경을 독립적으로 리뷰합니다. 코드는 바꾸지 않습니다.

계획: <docs/superpowers/plans/...md 경로>
비교: git diff main...<branch>
리뷰를 돌린 조건: <docs/orca.md의 조건 번호>

규칙:
- sources/, work/, raw/, assets/audio/, .env* 는 읽지 않습니다(절대 경로 포함).
- 계획 범위를 벗어난 변경, 안전 경계(scripts/production.py, scripts/common.py, .claude/, config/, AGENTS.md, orca.yaml) 약화, 테스트 약화, 렌더 결과에 영향을 주는 회귀를 우선 봅니다.
- 각 지적에는 파일:줄, 실패 시나리오, 근거를 붙입니다. 추측은 추측이라고 표시합니다.

완료 보고(worker_done, --outcome succeeded|failed):
- 판정: 병합 가능 / 수정 필요
- 지적 목록(심각도 순)
```
