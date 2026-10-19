# vlog-me 적대적 검토와 수정 검증

후속 변경: native Studio 실행을 읽기 전용 영상 뷰어로 교체했습니다. 현재 시작·미리보기 동작과 증거는 [전환 보고서](preview-only-review.md)를 기준으로 합니다. 아래 기록은 해당 검토 시점의 사실입니다.

검토 기간: 2026-10-18–19 · Asia/Seoul

설계와 현재 구현을 대조해 문제 9건을 재현했습니다. 8건은 수정했고 Studio의 기본 실행 설정 1건은 보완한 뒤 남은 한계를 기록했습니다. **Claude Code 시작, 기존 Skill 호출, 합성 run의 상태 저장·재개 경로는 검증을 통과했습니다.** 고정된 Remotion version의 공식 CLI에서 완전한 read-only 옵션은 확인하지 못했습니다.

이번 범위는 구축된 환경의 검토·수정입니다. 최근 30일 전체 업무 발굴은 수행하지 않았습니다. 실제 원본 영상·사진을 읽거나 처리하지 않았고 음원·ASR model을 다운로드하지 않았습니다. 새 dependency, Custom Skill, 상시 subagent, automation도 추가하지 않았습니다.

## 검토 방법과 범위

- 기준: [환경 설계](../docs/superpowers/specs/2026-10-18-vlog-environment-design.md), [작업 절차](../docs/workflow.md), `CLAUDE.md`, 현재 config·scripts·renderer·tests.
- 주 검토: 설계의 주장별로 반례를 만들고 시작 환경·권한 범위·Skill 무결성·상태 전이를 확인했습니다.
- 독립 검토: 대화 이력을 전달하지 않은 별도 context 두 개에서 설계 659행과 관련 구현을 읽었습니다. 하나는 상태·중단·재개, 다른 하나는 Claude/Skill·Studio 연동을 담당했습니다. 최초 검토 결과를 받은 뒤 테스트·수정을 위임했으며, 이 후속 작업을 새로운 독립 검토로 계산하지 않았습니다.
- 변경 전 source/docs/config/Skill/report 189개 파일의 사본과 hash를 `/private/tmp/vlog-me-review-znd48_qn`에 보존했습니다. dependency와 원본 미디어는 복사하지 않았습니다.
- 시작 검사도 PASS였지만 반례가 통과했습니다. 기존 Python 7개 테스트만으로 아래 실패 상황을 다루지 못했습니다.

## 발견한 문제와 수정

모두 로컬 setup 동작의 P2 결함으로 분류했습니다. 성공한 테스트 수보다 실패 재현과 수정 후 거부·보존 동작을 근거로 판정했습니다.

| ID | 수정 전 실패 조건 | 수정 내용 | 수정 후 근거 |
| --- | --- | --- | --- |
| R1 | 실행별 brief가 있어도 전역 새-run 기본값 변경으로 완료 결과가 stale이 됨 | fingerprint는 저장한 brief를 사용하고 미사용 음원 목록·현재 기본값을 제외. 현재 권한 검사는 별도 유지 | frozen default 회귀 테스트, 새 process의 결과 재사용 |
| R2 | Ctrl-C가 Python lock만 풀고 실행 중인 하위 process를 남길 수 있음 | timeout·예외·중단 시 소유한 process group에 TERM, 필요 시 KILL 후 회수. state에 paused 기록 | 실제 작은 Python child에 SIGINT를 보낸 회귀 테스트 |
| R3 | FFmpeg 실패 후 manifest가 없으면 status 조회 실패. inventory 실패는 상태 기록 밖에서 발생 | run 할당부터 fixture_generation 상태·lock을 만들고 준비 전체의 오류 기록. manifest 없는 실패 조회 지원 | 생성·inventory 실패, 잘못된 state owner/run ID 검사 |
| R4 | 렌더 도중 생긴 audio-credits.md를 마지막 write_text가 덮어씀 | 안전 경로 검사와 exclusive create로 기존 파일 보존 | 기존 credit이 생기는 반례에서 실패·원본 내용 보존 |
| R5 | Studio props가 첫 실행에서 고정되고 재실행·canonical timeline 갱신이 막힘 | props+owner hash 검증, 같은 입력 재사용, 명시적 --refresh, 중간 실패 시 덮어쓰기 거부 | 9개 Studio 테스트, 실제 재실행·caption 갱신 화면 |
| R6 | Studio 기본 편집·Ask AI·agent 선택이 Claude-only 운영 경로와 어긋남 | 편집 제스처·Ask AI 제한, 기본 agent를 Claude Code로 선택, 우회 UI 사용 금지와 보장 한계 명시 | 명령 인자 테스트, 실제 terminal의 Open agent (Claude Code), native source 확인 |
| R7 | doctor 검사와 지침만 있고 write helper가 현재 scope 변경을 다시 확인하지 않음 | 생성·렌더·Studio·Node validator 진입점과 준비 완료/영상 확정 전 scope 확인. 저장한 brief도 제한 검사 | 시작 전·준비 중·렌더 중 scope 변경 거부 및 artifact 보존 |
| R8 | doctor의 assert 검사가 python -O에서 사라짐. 등록 Skill 외 파일도 검출하지 않음 | 명시적 오류 검사와 Skill 전체 file set/hash·entrypoint 대조 | 최적화 mode, 변조·추가 파일·미등록 Skill 거부 테스트 |
| R9 | init.sh 후 일반 claude 실행은 프로젝트 Node/npm PATH를 상속하지 않음 | env.sh를 읽고 project cwd에서 exec하는 claude.sh 추가, 시작 문서 수정 | 격리된 fake Claude/Node로 cwd·PATH·인자 검사, 실제 Claude Skill 호출 |

R1–R6은 두 독립 reviewer가 보고했고 R7–R9는 주 검토에서 확인했습니다. 수정 후 source·tests·저장된 실행 기록을 다시 읽은 reviewer는 추가로 근거가 확인된 P1/P2 회귀를 발견하지 못했습니다. 이는 최초 검토의 후속 확인이며 별도의 cold review나 재실행 결과는 아닙니다. R6은 설정과 운영 경로를 보완한 것이며 native Studio의 모든 agent/write API를 차단한 것은 아닙니다.

## 검증 결과

| 검사 | 결과 | 근거 |
| --- | --- | --- |
| init.sh | PASS | [최종 로그](adversarial-verification-final.log): Python 29개, Node 2개, compileall, ESLint, TypeScript, 도구·scope·Skill 검사 |
| Claude Code 실제 Skill 연동 | PASS | [기록](claude-review-check.json): Skill 광고뿐 아니라 Skill(remotion-best-practices) 호출과 reference 읽기 확인, permission denial 0 |
| 시작 환경 전달 | PASS | tests/test_startup.py의 fake binary로 PATH·cwd·인자 전달 확인. 별도 model이나 coordinator 없음 |
| 합성 encoded output | PASS | [run 기록](adversarial-run.json), [QA](../work/synthetic-20261018-145659-bb6031a1/verify.json) |
| 별도 process에서 status/render 재호출 | PASS | succeeded, 파일 mtime 유지, lock 해제. [기록](adversarial-run.json) |
| Studio 재실행·refresh | PASS | 같은 props 재사용, 4초 합성 timeline과 수정 caption 표시. [기록](studio-review.json), [화면](studio-review.png) |
| 범위·경로·실패·중단 반례 | PASS | 기존 7개에 복구 10개·Studio 9개·시작 3개를 추가. 모의 데이터와 합성 fixture만 사용 |
| Shell·JSON·문서 링크·최종 변경 범위 | PASS | [마감 검사](adversarial-closeout.json) |
| 실제 원본·ASR·무료 음원·플랫폼 검사 | NOT_RUN | 사용자 제한 유지, 음원 목록 비어 있음 |
| 사람의 전체 시청·청취, 장시간·4K | NOT_RUN | 짧은 합성 입력만 검사 |

최종 성공 run은 `synthetic-20261018-145659-bb6031a1`입니다. 테스트 영상 4초와 사진 2초를 합쳤으며 본편 길이 정책과 무관합니다. 출력은 1280×720, 30fps, H.264/AAC입니다. 렌더·검사 구간은 18.87초이며 저장된 preview의 측정값은 -26.14 LUFS, true peak -18.63 dBTP입니다. `verify.json`의 output_*는 loudnorm 분석의 예상값이므로 실제 정규화 결과로 해석하지 않습니다.

Claude Code 읽기 검증의 CLI 보고 비용은 USD 0.0895534입니다. 실행 도구는 Read와 Skill로 제한했고 원본·음원을 전달하지 않았습니다. 이 검증은 Skill 호출·지침 이해의 증거이며 Claude가 전체 제작을 완수한 benchmark가 아닙니다. 이후 수정한 Studio 한계 문구까지 model이 다시 읽었다고 주장하지 않습니다.

## 남은 한계와 보류

**Native Studio는 read-only 보안 경계가 아닙니다.** 고정된 Remotion 4.0.536 source에서 두 disable flag는 편집 제스처와 Ask AI를 제한하며 모든 server write/agent API를 막지 않습니다. Codex 내장 브라우저의 annotation bridge가 있으면 Generate with agent가 계속 표시됩니다. --coding-agent=claude-code도 기본 선택일 뿐 다른 agent를 차단하지 않습니다. 검증 중 해당 동작을 실행하지 않았습니다.

따라서 지원하는 작업 경로는 Claude Code → canonical timeline → 프로젝트 helper입니다. Studio는 재생·미리보기만 사용하며 편집·Generate/agent·설치·Studio render UI는 사용하지 않습니다. 이 제한을 README·CLAUDE.md·workflow에 함께 기록했습니다. 현재 코드에서 공식 read-only CLI와 loopback-only bind 옵션을 확인하지 못했고, 서버의 외부 접근 가능 여부는 검사하지 않았습니다. 검증용 서버와 탭은 종료했습니다. 이를 완전히 격리하려면 별도 viewer나 실행 경계가 필요한데 이번 수정에 새 framework·vendor patch를 추가하지 않았습니다.

상태 재개는 **완료 결과의 검증된 재사용**과 **아직 렌더하지 않은 pending 입력의 검증**입니다. 실패한 render를 이어 붙이는 checkpoint 기능은 아닙니다. 실패·paused·stale·partial·잔여 lock은 보존하며 새 합성 run으로 검증합니다. SIGKILL·전원 중단의 cleanup은 보장하지 않습니다.

실제 ingestion·ASR·장면 선별·예능 caption·음원 선택·게시 검증은 미구현 상태를 유지합니다. 안전한 음원이라는 판단은 아직 한 건도 내리지 않았습니다. 기존 Skill 원문과 lock을 그대로 유지했고 새 Skill A/B 평가는 해당하지 않습니다.

## 실패 기록과 변경 보존

이번 검증에서도 기본 sandbox의 Studio/렌더는 No available ports found로 실패했습니다. `synthetic-20261018-145641-3f53e230`의 failed state와 artifact를 보존했습니다. 허용된 localhost/browser 실행 범위로 새 run을 만들어 통과했으며 실패 run을 성공으로 덮어쓰지 않았습니다. 자동 승인 검토의 거절은 없었습니다.

시작·종료 시 Git repository가 아니므로 git status는 exit 128입니다. Git init·commit·push는 하지 않았습니다. snapshot과 현재 파일 hash를 비교해 변경 범위를 확인했습니다. 원본 설계, official Skill 143개 파일, dependency manifest/lock, config와 기존 report evidence를 보존했습니다. setup-report에는 역사적 기록임을 알리는 링크만 추가했습니다. 새 실행 자료는 work/와 reports/에 있습니다.

전역 설정·credential·.env·다른 프로젝트는 변경하지 않았습니다. `feature_list.json`, `progress.md`, `session-handoff.md`에 최신 결과와 시작 명령을 반영했습니다. 새 설치나 외부 활성화는 없으며 현재 setup 수정을 마치기 위해 추가 승인이 필요한 항목은 없습니다.

## 다음 세션

```bash
cd /Users/soom.kang/Desktop/work/2.services/vlog-me
./init.sh
./scripts/claude.sh
```

현재 상태를 설명하거나 합성 fixture를 검증할 수 있습니다. 원본 처리·음원 다운로드·본편 렌더를 자동으로 시작하지 않습니다. 구현 코드를 바꾸면 과거 완료 run이 stale이 되는 것은 정상이며, 검증 없이 fingerprint를 갱신하지 않습니다.
