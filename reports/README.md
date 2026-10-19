# 보고서 색인

최신 근거부터 확인합니다. 파일은 다른 보고서에서 경로로 참조하므로 옮기거나 지우지 않습니다.

## 현재 기준

- [first-sample-review-2026-10-19.md](first-sample-review-2026-10-19.md): 첫 실제 sample(vietnam-20260527) 후보 리뷰까지의 진행·제한
- [preview-only-review.md](preview-only-review.md): 현재 시작·미리보기 동작, 검증, 제한
- [project-review-2026-10-19.md](project-review-2026-10-19.md): 실제 제작 목표 기준의 적대적 리뷰와 개선 계획
- `unit4-expected-frame-synthetic.jpg`: 단위 4 기대 화면 still 예시(합성 영상, 단위 5 이전의 시스템 폰트)
- `unit5-caption-gallery.jpg`: 단위 5 자막 preset 14종 갤러리(번들 폰트). `node renderer/scripts/gallery.mjs`로 다시 만듭니다
- `preview-only-checks.log`, `preview-only-lifecycle.json`, `preview-only-browser.json`, `preview-only-viewer.png`: 위 전환의 최종 실행 증거

## 과거 기록 (해당 시점의 사실)

- [setup-report.md](setup-report.md): 최초 환경 구축. `local-verification*.log`, `final-run.json`, `resume-check.json`, `claude-check.json`, `claude-skill-check.json`, `harness-assessment.json`
- [adversarial-review.md](adversarial-review.md): 첫 적대적 검토와 복구 수정. `adversarial-*.json`, `adversarial-verification*.log`, `claude-review-check.json`
- `studio-review.json`, `studio-review.png`: 제거된 native Studio 경로의 검증. 현재 동작이 아닙니다.
- `preview-only-http.json`, `preview-only-lifecycle-failed.json`, `preview-only-closeout.json`: 전환 중간 기록
