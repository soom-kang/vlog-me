# vlog-me: Claude Code 단독 브이로그 제작 환경 설계

작성일: 2026-10-18 · Timezone: Asia/Seoul  
상태: **환경 설계와 구축 기준**. 아래 미구현·검증 상태는 구축 전 설계 검토 시점의 기록입니다. 이후 시작한 환경 구축의 현재 구현 범위와 실행 증거는 [구축 보고서](../../../reports/setup-report.md)와 [작업 절차](../../workflow.md)를 우선합니다.

## 1. 구성 방향

**프로젝트명은 `vlog-me`이며, 이 프로젝트 안에 새 harness + Skills 구조를 구성합니다.** Claude Code 하나가 프로젝트 Skills를 불러와 로컬 미디어 도구를 실행하도록 설계합니다. 작업 규칙, 진행 상태, 데이터 계약, 검증 절차를 harness로 묶어 긴 촬영본도 여러 세션에 걸쳐 이어서 편집할 수 있게 합니다. 새 구조를 구성하되 검증된 기존 Skills와 도구부터 재사용합니다.

사용자가 확정한 조건은 다음과 같습니다.

- 실행 agent는 Claude Code입니다.
- Skills와 harness를 조합해 제작 과정을 진행합니다.
- 입력은 길이가 다양한 영상과 사진입니다.
- 결과물은 여행·일상·취미·행사 등 전반적인 YouTube 롱폼 브이로그입니다.
- 브이로그 유형과 핵심 이야기는 매 제작의 시작 프롬프트에서 확인합니다.
- 화면·호흡·caption의 톤은 해당 제작의 brief에 맞춥니다.
- 완성본 길이를 미리 고정하지 않습니다.
- 무료 BGM·효과음을 풍부하게 활용하는 사운드 편집을 포함합니다.
- 음원은 TikTok·Instagram·YouTube 모두에서 저작권 문제 없이 사용할 수 있는 것을 원합니다. 이를 위한 선별 기준과 자동 감지의 한계는 8절에서 구분합니다.
- 설계의 목적은 기반 환경 구성이며, 실제 원본 처리와 음원 확보는 별도 단계입니다.

이 설계는 다른 프로젝트의 코드, schema, 실행 환경, 승인 기록, 절대경로에 의존하지 않습니다. 사용자는 Claude Code에서 제작을 진행하며 별도 coding agent로 작업을 넘기지 않습니다. 최초 운영은 주 세션의 순차 실행으로 시작합니다. 긴 촬영본을 하나의 context에 모두 넣는 방식까지 고정하지는 않습니다. 먼저 저장된 근거를 필요한 범위만 읽도록 구성하고, 실제 병목이 확인되면 Claude Code 내부의 제한된 subagent를 검토할 수 있습니다. 초기에는 Custom Subagent와 별도 coordinator를 만들지 않습니다.

앞서 요청한 예쁜 구도·예능 자막·재미 60%/감성 40%는 사용자의 스타일 참고값으로 보존합니다. 모든 브이로그에 강제하지 않고 현재 프롬프트를 우선합니다. 이 취향을 상속했다면 brief에 그 사실을 기록합니다. `60:40`을 쓰는 경우에도 정확한 시간 할당보다 편집 방향으로 해석하는 것을 제안합니다. 강민경은 사용자가 제시한 취향의 참고점이며, 특정 영상의 편집 공식을 분석한 상태는 아닙니다.

사운드의 기본 제안은 장면별 음악 전환·짧은 강조음·현장음·쉼을 다양하게 사용하는 `rich_contextual`입니다. 모든 컷에 효과음을 넣거나 BGM을 계속 크게 재생하는 식으로 수량을 목표화하지 않습니다. 실제 밀도와 장르는 제작별 프롬프트와 sample 청취에서 정합니다. 무료 음원의 범위와 이용 조건은 8절에 정리합니다.

세 플랫폼 조건은 음원 재사용 범위에 적용합니다. 현재 결과물은 YouTube 롱폼이며, 이 조건만으로 TikTok·Instagram용 세로 영상 제작이나 업로드까지 작업 범위를 넓히지 않습니다.

### 프롬프트에서 유형과 방향 확정

실제 제작을 시작할 때 프롬프트의 `vlog_type`, 핵심 이야기, 편집 톤을 `work/<run_id>/brief.json`에 정리합니다. 명확한 내용을 다시 질문하지 않고, 판단에 영향을 주는 누락·충돌만 확인합니다. 파일명·촬영 장소만 보고 여행 브이로그로 분류하지 않습니다. setup 단계에는 실제 유형이나 원본 경로가 없어도 됩니다.

| 유형 예 | 선별할 이야기의 예 | 적용 원칙 |
| --- | --- | --- |
| 여행 | 이동·장소·사람·예상 밖 상황과 분위기 | 장소 이동 순서나 날짜별 분할을 강제하지 않음 |
| 일상 | 하루의 변화·작은 사건·반복 속 차이·관계 | 잔잔한 호흡과 현장음을 불필요한 무음으로 단정하지 않음 |
| 취미·요리·작업 | 과정·시도·실패·발견·완성 | 결과 이해에 필요한 과정을 길이 때문에 생략하지 않음 |
| 행사·기타·혼합 | 프롬프트에서 정한 핵심 사건과 관점 | 유형 세부 설명과 반드시 남길 내용을 확인 |

이 표는 선택 가능한 예시입니다. 유형별로 별도 Skill이나 pipeline을 만들지 않고 같은 harness에 brief와 필요한 reference를 전달합니다. 새 프롬프트가 기존 brief를 바꾸면 story·caption·관련 승인의 유효성을 확인합니다. source와 분석 조건이 같으면 기존 inventory·전사 등 기술 분석 cache는 재사용하고 창작 판단의 변경 범위만 다시 검토합니다.

## 2. 리서치에서 가져올 부분과 조정할 부분

첨부 3개를 설계 자료로 검토하고, 설치·동작 주장은 공식 문서와 공개 source로 보완했습니다. 첨부 안의 구축·전사·렌더·commit 명령은 이번 작업의 실행 권한으로 취급하지 않습니다.

| 리서치 제안 | 이번 프로젝트의 판단 | 반영 방식 |
| --- | --- | --- |
| 환경 구축과 실제 제작 분리 | 채택 | 합성 미디어로 환경을 검증하고 실제 원본 처리는 다음 단계로 구분 |
| 여러 coding agent 사이의 역할 분담 | 제외 | Claude Code 주 세션에서 Skills를 전환하며 작업 |
| 원본·중간 파일·최종 결과 분리 | 채택 | 원본은 보존하고 파생 파일을 `work/`와 `output/`에 기록 |
| `/watch`로 영상 근거 추출 | 조건부 채택 후보 | 긴 원본의 구간 탐색 보조로 평가. engine·전사 backend·전송 경로를 명시 |
| 공식 Remotion Skills | 채택 권장 | `remotion-best-practices`를 중심으로 필요한 reference만 사용 |
| story·예능 caption Custom Skills | 필요할 때만 추가 | 기존 Skill과 프로젝트 문서가 처리하지 못하는 반복 규칙만 분리 |
| 사진 전용 Skill·slideshow·beat-sync 일괄 추가 | 초기 구성에서 보류 | 사진은 story 선별과 renderer의 image 지원으로 먼저 처리 |
| 날짜별 3편·편당 15분 | 제외 | 이야기와 유효 장면을 기준으로 길이·편수 제안 |
| 처음부터 모든 원본을 완전 자동 제작 | 단계적 적용 | 취향과 기술 경로를 확인한 뒤 분석 범위와 실행 범위를 넓힘 |
| 설치 완료를 편집 가능 상태로 간주 | 제외 | 실제 composition·전사·시간 매핑·실패 경로를 따로 검증 |

### 공개 Skill에서 확인한 중요한 제약

- `/watch`는 frame·transcript 근거를 제공하지만 sampling으로 모든 사건을 관찰하는 것은 아닙니다. 현재 source에는 local engine과 외부 engine이 모두 있고, local WhisperX 경로도 기본적으로 alignment를 수행하지 않습니다. 따라서 단어 단위 컷 경계를 자동으로 보장하는 전사기로 취급하지 않습니다. [Watch source](https://raw.githubusercontent.com/bradautomates/claude-video/main/skills/watch/SKILL.md).
- `/watch`를 사용한다면 local engine과 허용한 전사 backend를 명시합니다. 기존 credential이 있다는 이유로 외부 engine을 선택하지 않으며, 긴 원본은 구간별로 탐색합니다. 설치 source의 credential 처리 지시보다 프로젝트의 보안 규칙을 우선합니다.
- 공식 Remotion 저장소에는 `remotion-best-practices`, `remotion-markup`, `remotion-captions` 등 관련 지침이 있습니다. 초기에는 포괄 Skill과 필요한 reference를 이용하고 같은 지침을 프로젝트 Skill에 복사하지 않습니다. [Remotion Skills](https://github.com/remotion-dev/skills).
- 커뮤니티 `video-editing`은 편집 절차의 참고 자료로 둡니다. 전체 절차를 함께 활성화하면 프로젝트 workflow와 선별·승인 규칙이 중복될 수 있어 기본 구성에서는 제외합니다. [Video Editing source](https://github.com/agenticluke/claude-skill-video-editing-plus).
- `video-use`는 실제 편집 helper가 있는 대안입니다. 현재 확인한 source는 ElevenLabs 전사, audio-first 절차, 별도 agent 작업 등을 포함하므로 이번 기본 workflow에는 활성화하지 않습니다. 대화 중심 촬영본에서 별도 비교할 수 있으며, 유용한 helper를 채택하더라도 license·입출력·외부 호출·cache를 검토합니다. [Video Use](https://github.com/browser-use/video-use).

**기존 Skill과 프로젝트 harness를 먼저 사용하고, Custom Skill은 반복되는 빈틈이 확인될 때 추가하는 순서**를 권장합니다. 아래 3개 프로젝트 Skill은 후보이며 필수 설치 목록이 아닙니다. 초기에는 `CLAUDE.md`와 workflow 문서로 시작할 수 있습니다. 고정적인 metadata·schema·decode 검사는 작은 script로 처리하고, 장면 선택과 문구처럼 판단이 필요한 절차만 필요에 따라 Skill로 분리합니다.

## 3. Skills, harness, 실행 도구의 역할

| 구분 | 역할 | 프로젝트에서 맡길 것 |
| --- | --- | --- |
| Claude Code | 현재 요청을 해석하고 도구를 호출하는 실행 주체 | 분석·선별·편집·검증 순서 진행 |
| Skills | 특정 작업의 절차와 판단 기준 | workflow 운영, story 선별, 예능 caption 초안, Remotion 구현 지침 |
| Harness | 작업 범위·상태·근거·재개·완료 조건 | `CLAUDE.md`, 파일 계약, 상태 기록, 검증 script, 필요한 hook |
| 로컬 도구 | 실제 미디어 처리 | FFmpeg/ffprobe, 전사 도구, image decoder, Remotion |

Skill을 설치해도 ASR model이나 caption composition이 자동으로 구현되는 것은 아닙니다. 반대로 모든 미디어 기능을 별도의 자동화 플랫폼으로 개발할 필요도 없습니다. 검증된 도구를 Claude Code가 호출하고, 반복 오류가 생기기 쉬운 경로·시간·출력 검사를 작은 helper로 고정합니다.

렌더 경로의 기본 제안은 **Remotion의 단일 timeline으로 영상·사진·자막을 합성하고, FFmpeg는 전처리·오디오 보조·검증에 사용하는 구성**입니다. 자막만 바꿨을 때도 같은 timeline을 재사용할 수 있게 합니다. 전체 렌더 비용이 실제 sample에서 부적합하면 경로를 재검토하며, 초기부터 두 개의 독립 renderer를 유지하지 않습니다. Remotion의 로컬 CLI 렌더 기능은 공식 문서에서 확인했습니다. [Remotion Rendering](https://www.remotion.dev/docs/render).

### 기존 기능과 새로 연결할 기능

아래는 구현 책임을 나눈 표입니다. 기존 도구의 기능과 프로젝트에서 검증된 기능은 다릅니다. 구축 전에는 실행 검증이 없었으며 이후 결과는 구축 보고서에 기록합니다.

| 기능 | 기존 자산이 제공하는 부분 | 프로젝트에서 연결하거나 작성할 부분 | 첫 구축 범위 |
| --- | --- | --- | --- |
| 파일·stream 검사, frame 추출 | FFmpeg/ffprobe | 허용 경로 검사, source ID, inventory와 출력 연결 | 제한된 합성 영상·사진부터 연결 |
| 전사와 탐색 근거 | 선택한 로컬 ASR 또는 조건을 충족한 Watch | source 구간·정밀도·coverage 연결, 후보가 없는 구간의 재검토 | 한 분석 경로 선택. 한국어 정확도는 실제 sample에서 판정 |
| 이야기와 장면 선별 | Claude Code의 판단, 프로젝트 편집 지침 | 근거가 있는 moments·편집안 작성 절차 | 문서로 먼저 운영. 반복 gap이 있을 때만 Custom Skill |
| 영상·사진·caption 합성 | Remotion runtime과 공식 Skills의 구현 지침 | 프로젝트 composition, 편집안의 frame 변환, caption 기본 스타일 | 지원 format을 선언한 단일 timeline |
| 오디오 | FFmpeg와 renderer의 미디어 기능, 기존 Remotion 지침 | 무료 asset 등록·선곡/배치 근거·원음/BGM/SFX 혼합·출처 목록 연결 | 합성음으로 다중 track·fade·ducking 연결. 실제 무료 음원은 허용된 sample 단계에서 확인 |
| 변경·재개·검증 | 파일 저장, 기존 도구의 검사 결과 | 입력 revision 연결, state 갱신, 작은 validator | 필요한 artifact만 기록. 범용 workflow 엔진은 만들지 않음 |

### 첫 구축의 크기

첫 목표는 제한된 sample에서 **brief → 근거 → 편집안 → preview → 수정 → 재개**를 한 번 연결하는 것입니다. 환경 단계에서는 합성 source와 합성 편집안을 사용해 연결을 확인합니다. 실제 원본 처리가 허용된 다음 단계에서 장면 발견과 취향 적합성을 확인합니다.

- 첫 composition은 영상·사진·기본 caption·원음/BGM/SFX track을 지원합니다. 합성음으로 배치·fade·대사 구간의 BGM 감쇠를 확인하고 실제 음원 선곡은 다음 sample 단계에서 평가합니다. source와 출력 규격은 구축 점검에서 명시합니다.
- 지원하지 않는 format은 조용히 변환하거나 누락하지 않고 보류 목록에 남깁니다. 지원 범위를 넓힐 때 해당 fixture를 추가합니다.
- 모든 JSON schema, 장르별 Skill, graphic insert, 대규모 음원 수집기, 병렬 agent를 한꺼번에 만들지 않습니다. 작은 로컬 음원 목록에서 선택·배치·교체하는 기본 사운드 workflow부터 연결합니다.
- 새 helper가 필요하면 기존 기능으로 해결되지 않는 입출력·오류 처리 범위를 먼저 적습니다. 커스텀 미디어 엔진 개발로 확대하지 않습니다.

## 4. 권장 Skills 구성

### 먼저 검토할 기존 Skills

아래 추천은 공개 source와 로컬 Skill 내용을 읽고 판단한 결과입니다. 설계 작성 당시에는 설치하거나 실제 브이로그로 실행하지 않았으며, 이후 채택 ref와 설치 상태는 `config/skills-lock.json`에 기록합니다.

| 추천 수준 | 기존 Skill과 source | 사용 목적 | 조건과 중복 처리 |
| --- | --- | --- | --- |
| 기본 추천 | [`remotion-best-practices`](https://github.com/remotion-dev/skills) | composition·영상/사진·모션·렌더 지침 | 공식 통합 진입점. 프로젝트의 렌더 기준으로 사용 |
| 작업별 사용 | 같은 저장소의 `remotion-captions`, `remotion-markup`, `remotion-render`, `remotion-studio` | 자막 데이터·React 구성·렌더·preview | 같은 공식 묶음의 세부 지침. 다른 출처의 사본을 추가하거나 내용을 Custom Skill에 복사하지 않음 |
| 조건부 추천 | [`watch`](https://github.com/bradautomates/claude-video) | source timecode가 있는 frame·transcript 근거와 구간 탐색 | local engine·허용 backend를 명시. 모든 장면 관찰이나 word alignment를 보장하지 않음 |
| 필요한 장면에 추천 | [`broll-me`](https://github.com/soom-kang/broll-me) | 한국어 설명 카드·목록·chart·transparent panel 삽입 | 작은 개인 프로젝트의 beta. 별도 runtime과 실제 sample 검증 필요. 본편 편집이나 전사의 대체재는 아님 |
| 대화 중심 제작의 대안 | [`video-use`](https://github.com/browser-use/video-use) | transcript 기반 컷·FFmpeg helper·결과 검토 | ElevenLabs 비용·전송, agent 호출, output 경로·cache 규칙을 조정해야 함. 기본 workflow와 동시에 전체 절차를 활성화하지 않음 |

초기 조합은 **공식 Remotion Skills + 프로젝트 brief/상태/검증 harness**입니다. 원본 탐색에는 `/watch`와 project-local 분석 경로 중 검증된 한 경로를 선택합니다. `/watch`의 로컬 전사를 채택했다면 같은 용도의 다른 ASR을 동시에 설치하지 않습니다. `broll-me`가 만든 clip은 필요한 경우 본편 timeline의 입력으로 넣고 별도의 master timeline을 운영하지 않습니다.

사운드에도 기존 Remotion Skills·공식 오디오 문서와 FFmpeg를 먼저 사용합니다. 음원 서비스는 asset 공급처이고 Skill은 실행 지침이므로 둘을 구분합니다. 선곡·효과음 배치 규칙은 우선 `docs/editorial-guide.md`와 workflow에 추가하며, 반복되는 독립 절차가 확인될 때만 Custom Skill 후보로 분리합니다. 이번에는 음원 검색 Skill이나 유료 생성 서비스를 새로 도입하지 않습니다. 실제 오디오 API는 고정한 Remotion version에 맞춰 확인합니다. [Remotion audio](https://www.remotion.dev/docs/html5-audio).

`video-editing` 계열도 원본 구성·EDL·FFmpeg 절차를 참고할 수 있습니다. 다만 확인한 [ECC upstream](https://github.com/affaan-m/everything-claude-code/blob/main/skills/video-editing/SKILL.md)은 외부 생성 서비스와 별도 편집기의 마무리까지 포함하므로 Claude Code 단독·로컬 우선 구성에 그대로 채택하지 않습니다. 같은 역할의 fork를 여러 개 설치하지 않습니다.

2026-10-18의 directory 표시값으로는 Remotion 기본 Skill이 636.9K installs, watch가 16.6K, video-use가 4.7K였습니다. 인기도는 탐색 보조 정보이며 호환성·보안·영상 품질의 증거로 사용하지 않습니다. `broll-me`의 install 수는 확인하지 않았으며 작은 공개 프로젝트라는 한계를 함께 둡니다. [Remotion directory](https://www.skills.sh/remotion-dev/skills/remotion-best-practices), [Watch directory](https://www.skills.sh/bradautomates/claude-video/watch), [Video Use directory](https://www.skills.sh/browser-use/video-use/video-use).

### 설치 명령 참고

아래는 **향후 채택한 항목만 설치할 때의 참고 명령**입니다. 현재 실행하지 않았습니다. 기준 경로는 `/Users/soom.kang/Desktop/work/2.services/vlog-me`이며, Claude Code의 project scope를 대상으로 합니다. 등록 전에는 source·ref·의존성과 기존 설치를 확인하고, 선택한 revision을 `toolchain.json`에 기록합니다.

```sh
npx skills add remotion-dev/skills --skill remotion-best-practices --agent claude-code
npx skills add bradautomates/claude-video --skill watch --agent claude-code
npx skills add https://github.com/soom-kang/broll-me/tree/v0.8.0-beta.3 --skill broll-me --agent claude-code
```

기본 Skill이 참조하는 Remotion 세부 지침이 실제 설치 결과에 포함되는지 확인하고, 빠진 항목만 같은 source/ref에서 추가합니다. 위 명령은 `--global`을 사용하지 않는 Skills CLI 경로입니다. plugin으로 설치한다면 별도 방식으로 중복 설치하지 않으며 marketplace 등록이 사용자 설정을 바꿀 수 있다는 점도 확인합니다. [Skills CLI](https://github.com/vercel-labs/skills), [Claude plugin scope](https://code.claude.com/docs/en/discover-plugins).

### Watch 채택 전 통합 조건

**Skill의 project scope 설치는 그 Skill이 실행하는 setup·cache·설정의 project scope를 보장하지 않습니다.** 현재 Watch source는 사용자 설정을 `~/.config/watch/.env`, 관리 환경을 `~/.cache/watch/whisperx-venv`에 두며 model cache도 사용자 홈을 사용합니다. 따라서 위 설치 명령만으로 프로젝트 격리가 끝났다고 판단하지 않습니다. [Watch setup과 runtime 경로](https://raw.githubusercontent.com/bradautomates/claude-video/main/skills/watch/SKILL.md).

1. 채택할 source/ref의 setup과 실행 경로를 읽고 설정·환경·model cache·결과 파일의 실제 쓰기 위치를 정리합니다. preflight라는 이름만 보고 읽기 전용으로 간주하지 않습니다.
2. CLI나 문서화된 설정으로 프로젝트 경로를 지정할 수 있는지 확인합니다. 지원하지 않는 경로 override를 발명하지 않습니다.
3. 프로젝트 범위가 불가능하면 Watch 채택을 보류하고 project-local 분석 경로를 사용합니다. 공유 환경이 필요한 경우에는 영향 범위를 설명해 사용자가 선택한 뒤에만 예외로 기록합니다. 다른 구성 작업은 계속할 수 있습니다.
4. 허용된 설치 단계에서는 대상 경로의 변경 전후를 확인합니다. 기존 credential이나 사용자 설정은 임의로 수정하지 않습니다.
5. 실행에는 `local` engine과 허용한 ASR backend를 명시하고 결과는 해당 run으로 연결합니다. 설정·경로·backend 계약을 통과하기 전에는 제작 기본 경로로 등록하지 않습니다.

로컬 ASR·frame 추출과 Claude Code가 그 자료를 읽는 것은 별개의 데이터 흐름입니다. `external_processing: false`는 추가 미디어 provider 사용을 끈다는 뜻이며 Claude Code까지 포함한 완전한 오프라인 처리를 뜻하지 않습니다.

### 필요할 때 만들 프로젝트 Skill 후보

아래는 **조건부 명세**입니다. 현재 설치되어 있거나 실행 가능한 명령이 아닙니다. 기존 Skill·프로젝트 문서로 충분하면 만들지 않습니다.

| Skill | 호출 시점과 필수 입력 | 절차와 출력 | 종료 조건 |
| --- | --- | --- | --- |
| `vlog-workflow` | 사용자가 setup·제작·resume을 요청. 현재 요청 범위와 `work/<run_id>/state.json` | 실제 제작에서는 프롬프트의 유형·톤을 `brief.json`에 정리. 현재 단계·입력 hash·허용 범위를 확인하고 필요한 Skill과 도구 호출 | 요청한 단계 완료 또는 필수 입력·승인·검증 부족 시 정지 |
| `vlog-story-editor` | 현재 brief, 검증된 inventory, 해당 source의 전사 또는 시각 근거 | 유형과 이야기·톤에 따라 장면 선별. 사진도 함께 검토해 `moments.json`, `story.md`, `edit_decisions.json` 초안 작성 | source 구간·선택/제외 이유·불확실성·예상 러닝타임을 제시하고 편집안 검토에서 정지 |
| `k-variety-caption-director` | 예능형 caption을 선택한 brief, 채택된 편집안·timeline·moments·style. dialogue가 있으면 전사 필요 | 실제 발화와 편집자 코멘트를 구분. `captions.json`과 확인 필요 목록 작성 | 문구·근거·출력 시간·표시 충돌 확인 완료 또는 불확실 cue 보류 |

### 호출과 범위

- 프로젝트 Skill의 canonical 위치는 `.claude/skills/<skill-name>/SKILL.md`입니다.
- `vlog-workflow`를 만들면 사용자가 시작할 때 호출하도록 `disable-model-invocation: true`를 제안합니다. 이미 허용된 단계 안에서는 매번 재승인을 요구하지 않습니다.
- story·caption Skill은 초기에는 허용된 작업 범위에서 주 세션이 사용합니다. 초기 구성에 `context: fork`나 별도 agent 설정을 두지 않으며, 이후 context 분리가 필요하면 7절의 기준으로 검토합니다.
- 원본 분석·render까지 허용되지 않은 caption 초안 요청에서 상위 workflow를 자동으로 확대하지 않습니다.
- 단순 metadata 수집, render의 고정 검사, 사진 중복 후보 계산은 별도 전문 agent나 Skill로 분리하지 않습니다.

Claude Code의 프로젝트 Skill 경로와 직접 호출·자동 호출 제어는 공식 기능입니다. 실제 설치 후에는 명령 목록과 이름 충돌을 확인합니다. 같은 내용을 `.claude/commands/`에도 중복 등록하지 않습니다. [Claude Code Skills](https://code.claude.com/docs/en/skills).

### 입력 parameter와 기본값

| Parameter | 용도 | 기본값·누락 처리 |
| --- | --- | --- |
| `run_id` | 한 제작의 상태·artifact namespace | setup에는 synthetic run 사용. 실제 제작에서는 고유 ID 필요 |
| `phase` | 이번 호출에서 허용한 단계 | 명시되지 않으면 현재 요청과 상태에서 해석. 모호하면 쓰기·원본 처리를 시작하지 않음 |
| `source_roots` | 허용한 원본 경로 | setup에서는 비어 있음. 실제 분석 전에 경로 범위 확인 |
| `vlog_type` | 현재 제작 유형을 `travel`, `daily`, `other`로 정리. 구체적인 설명은 보존 | setup에서는 미지정. 실제 제작은 프롬프트에서 확인하며 기존 run의 값을 자동 상속하지 않음 |
| `vlog_type_detail` | 기타·혼합 유형의 설명 | 프롬프트의 구체적인 주제와 관점을 기록 |
| `runtime_policy` | 길이 결정 방식 | `content_driven`, 고정 분량 없음 |
| `editorial_direction` | 재미·감성·기록성 등 현재 편집 방향 | 프롬프트 우선. 이전 취향을 상속하면 brief에 명시. setup에서는 미확정이며 시간 quota로 사용하지 않음 |
| `caption_style` | 기본·예능·절제 등 자막 방향 | 현재 brief를 따름. 예능형 Skill을 모든 유형에 자동 적용하지 않음 |
| `sound_design` | BGM·효과음의 역할과 밀도 | 기본 제안은 `rich_contextual`. 현재 프롬프트와 sample 청취 결과로 조정 |
| `audio_asset_policy` | BGM·효과음의 취득·이용 비용 | `free_only`. 유료 asset·체험판·생성 서비스로 자동 전환하지 않음 |
| `audio_platforms` | 음원 이용 권한을 확인할 대상 | `youtube`, `instagram`, `tiktok` 모두. 실제 게시 작업의 실행 권한과는 별개 |
| `attribution_policy` | 출처 표기 음원의 후보 포함 여부 | 표기 유무보다 세 플랫폼의 이용 권한·claim 위험을 우선. 초기에는 무표기 음원을 우선하는 제안 유지 |
| `analysis_budget` | 한 번에 처리할 범위·비용·resource 한도 | 후보가 없는 구간의 재검토 예산도 포함. 실행 전에 범위를 기록하고 소진 시 checkpoint 후 보류 범위 보고 |
| `external_processing` | 추가 외부 media provider 사용 | 기본 비활성. Claude Code에 제공할 자료 범위도 별도 확인 |

다음은 설정 의도를 설명하는 예시이며 아직 구현된 설정 schema는 아닙니다.

```json
{
  "agent_runtime": "claude-code",
  "use_subagents": false,
  "source_roots": [],
  "vlog_type": null,
  "vlog_type_detail": null,
  "runtime_policy": "content_driven",
  "target_duration_seconds": null,
  "editorial_direction": null,
  "caption_style": null,
  "sound_design": "rich_contextual",
  "audio_asset_policy": "free_only",
  "audio_platforms": ["youtube", "instagram", "tiktok"],
  "attribution_policy": null,
  "external_processing": false
}
```

좋은 호출 예는 “준비된 근거에서 이야기 흐름을 제안하고 컷 실행 전 멈춰 주세요”입니다. “자막 초안만 요청했는데 새 전사·음원 다운로드·전체 렌더를 시작하는 동작”은 범위 위반입니다.

예를 들어 “이번에는 잔잔한 일상 브이로그로, 평일 저녁의 요리와 작업 과정을 중심으로 편집해 주세요”라는 프롬프트는 `vlog_type: daily`와 해당 이야기·톤으로 기록합니다. 여행 이동 서사나 예능 자막을 강제하지 않고, 길이는 필요한 내용으로 결정합니다. “이번에는 여행 브이로그이며 앞서 정한 재미·감성 취향을 유지해 주세요”라는 요청은 그 취향을 해당 run에 적용합니다.

## 5. 최소 harness와 디렉터리

아래는 단계적으로 구성할 목표 구조입니다. 구축 전 `vlog-me`에는 이 설계 문서만 있었습니다. 첫 구축에서 빈 파일을 모두 만들지 않고 실제로 연결하는 단계의 입출력부터 작성합니다.

```text
vlog-me/
  CLAUDE.md
  README.md
  .gitignore
  .claude/
    settings.json
    skills/
      # 기존 Skills와 필요한 프로젝트 Skill만 등록
      # 공식 rendering Skill은 한 가지 설치 방식으로 등록
  config/
    project.json
    toolchain.json
    media-licenses.json
  assets/
    audio/                 # 허용된 단계에서 등록할 로컬 음원. Git 제외
  docs/
    editorial-guide.md
    workflow.md
    superpowers/specs/2026-10-18-vlog-environment-design.md
  reports/
    setup-report.md
  scripts/
    doctor.sh
    inventory.py
    validate.py
    smoke-render.sh
  renderer/
    package.json
    package-lock.json
    src/
  tests/
    fixtures/
  work/
    <run_id>/
      state.json
      brief.json
      inventory.json
      coverage.json
      transcripts/
      moments.json
      story.md
      edit_decisions.json
      timeline.json
      captions.json
      audio-credits.md     # 해당 timeline에서 사용한 음원의 표기 문안
      approvals/
      verify/
  output/
```

- `CLAUDE.md`에는 시작 시 읽을 자료, 원본 보호, 현재 단계, 검증 명령, 완료 기준만 둡니다. 세부 편집 방법은 Skills와 문서로 분리합니다.
- `state.json`은 단계와 현재 artifact hash, 완료한 작업, 실패·보류, 다음 행동을 기록하는 단일 진행 상태입니다. 재개할 때 실제 파일과 대조합니다.
- `brief.json`은 해당 run의 유형·핵심 이야기·톤·caption·sound 방향과 사용자 프롬프트 근거를 기록합니다. `resolved_config`에 해당 run에서 선택한 source·출력·resource·전송·음원 이용 정책과 취향 reference의 revision을 보존합니다. 진행 상태를 중복 관리하는 파일이 아닙니다.
- state가 없는 첫 setup은 허용된 구성 범위에서 초기 상태를 만듭니다. 기존 state가 손상되거나 artifact와 맞지 않으면 새 상태로 덮어쓰지 않고 복구가 필요한 항목을 보고합니다.
- `coverage.json`은 source 구간마다 어떤 근거를 확인했는지 기록하는 콘텐츠 검토 데이터입니다. 진행 상태와 목적이 다릅니다.
- `toolchain.json`에는 도구·Skill의 version 또는 고정 ref, 설치 범위, 검증한 executable 경로를 기록합니다. 다른 프로젝트의 사용자별 절대경로를 기본값으로 넣지 않습니다.
- `project.json`에는 새 run에 사용할 기본 output 규격·편집 방향·전송·resource 정책을 둡니다. 원본 경로를 기본값으로 제안해도 실제 처리 권한으로 간주하지 않으며, secret은 넣지 않습니다.
- `media-licenses.json`에는 사용할 asset의 hash·출처·이용 조건·확인 시점과 선곡용 metadata를 기록합니다. 오디오 실행 배치는 `timeline.json`에서만 관리하고, `audio-credits.md`는 그 사용 목록에서 생성합니다.
- 원본은 지정된 외부 폴더나 project 안의 명시적 source root에서 읽습니다. 불필요한 복사와 symlink 생성을 기본 동작으로 두지 않습니다.
- `work/`, `output/`, `assets/audio/`, 원본 경로, cache·가상환경·의존성·secret 파일은 Git에서 제외하도록 설계합니다. 음원 원본을 Skill·template·공개 저장소에 함께 배포하지 않습니다. 현재 Git 초기화나 commit은 하지 않습니다.

`CLAUDE.md`와 auto memory는 지침 context이며 강제 접근통제 설정이 아닙니다. 운영의 기준은 프로젝트 파일과 검증 결과에 두고, auto memory를 유일한 진행 기록으로 삼지 않습니다. [Claude Code Memory](https://code.claude.com/docs/en/memory).

### 기본값과 진행 중인 run의 관계

- 새 run에서는 현재 프롬프트를 우선하고, 사용자가 선택한 취향 reference와 프로젝트 기본값으로 비어 있는 항목을 보완합니다. 유형은 매 제작 프롬프트에서 확인합니다. 적용한 값과 출처를 brief에 저장합니다.
- 재개할 때는 저장된 run 설정을 사용합니다. 프로젝트 기본값이나 `editorial-guide.md`가 바뀌어도 진행 중인 run에 자동 반영하지 않습니다.
- 현재 run을 바꾸라는 명시적 요청이 오면 brief revision과 변경 이유를 남기고 8절의 의존 관계에 따라 결과를 다시 검토합니다. 이미 허용한 범위의 일반 작업마다 재승인을 요구하지 않습니다.
- 이전에 저장된 설정도 현재 권한 제한을 우회할 수는 없습니다. 현재 접근 범위와 충돌하면 해당 작업을 보류하고 이유를 보고합니다.

state는 단계별로 `pending`, `running`, `succeeded`, `failed`, `paused`, `stale`을 구분하는 것을 제안합니다. `succeeded`는 해당 단계의 출력 검증을 통과했을 때만 기록합니다. 중단된 `running`이나 일부 파일의 존재는 성공으로 복구하지 않습니다. 완료 출력은 임시 파일의 검증 후 확정하고, 실제 입력·출력 revision이 일치하는 결과만 재사용합니다. 구체적인 schema와 저장 방식은 첫 연결에 필요한 범위에서 확정합니다.

### Hooks와 권한

초기에는 별도 background 실행기 없이 script 검증으로 시작합니다. 실제 제작 범위를 여는 단계에서 필요한 `PreToolUse` hook만 작게 추가하는 것을 제안합니다.

- `.claude/settings.json`은 프로젝트 범위의 권한과 hook을 관리합니다. 사용자 전역 설정을 바꾸지 않습니다.
- hook은 알려진 위험 작업·보호 경로·현재 단계와 어긋난 도구 호출을 차단하거나 확인을 요청하는 보조 장치입니다.
- hook에서 ASR·render·다른 Claude 세션을 자동 실행하지 않습니다.
- shell 문자열 일부를 찾는 규칙만으로 모든 쓰기·외부 전송을 차단했다고 주장하지 않습니다. 다양한 호출 형태와 실패 시 동작을 검증해야 합니다.
- 실제 helper에도 realpath·원본/출력 분리·허용 확장자·기존 출력 보호 검사를 둡니다. 더 강한 원본 보호가 필요하면 OS 수준의 읽기 전용 접근을 별도 검토합니다.

도구 호출 전 hook의 decision 기능과 Bash permission pattern은 공식 문서에서 확인했습니다. 실제 설정은 설치한 Claude Code 버전에 맞춰 검증하며, 이 문서는 아직 설정 파일을 제공하거나 활성화하지 않습니다. [Hooks](https://code.claude.com/docs/en/hooks), [Permissions](https://code.claude.com/docs/en/permissions).

## 6. 로컬 도구 구성과 설치 우선순위

| 도구 | 목적 | 권장 |
| --- | --- | --- |
| Claude Code | 전체 작업의 실행 주체 | 필수. 실제 project에서 Skill·지침 로딩 확인 |
| FFmpeg / ffprobe | stream 검사·proxy·오디오 보조·decode 검증 | 필수. 기존 설치를 먼저 확인 |
| Python / uv | metadata·검증 helper와 로컬 전사 환경 | project별 환경과 lock으로 재현 |
| Node.js / npm / TypeScript / Remotion | 단일 timeline과 caption composition | 우선 연결할 구성안. 지원 버전·dependency·lock을 고정하고 긴 영상의 적합성은 부하 검증으로 판정 |
| 로컬 ASR | 한국어 대사와 timestamp | Apple Silicon이면 `mlx-whisper`를 우선 비교 후보로 제안. runtime·model 검증 후 한 backend 선택 |
| image decoder / ExifTool | HEIC·orientation·촬영 metadata | 실제 지원 범위를 확인하고 필요한 것만 추가 |
| `/watch` | frame·transcript 기반 구간 탐색 | 조건부 선택. 기본 탐색 경로와 역할이 겹치면 추가하지 않음 |
| PySceneDetect | 긴 연속 영상의 scene 후보 추출 | scene 탐색이 병목일 때 추가 |
| `broll-me` | 설명 카드·graphic insert | 필요한 장면에만 선택. 생성한 clip을 본편 timeline의 입력으로 사용 |
| slideshow·map·beat-sync·Manim | 특수 연출 | 첫 기본 환경에서는 보류. 예를 들어 지도는 여행 유형에서도 필요한 경우에만 선택 |

로컬 ASR의 선택은 한국어 원음·겹말·고유명사·웃음·word timestamp를 포함한 작은 sample로 결정합니다. model을 모두 설치해 두지 않습니다. `/watch`를 채택하더라도 정밀 컷용 word alignment는 별도 요구로 검증합니다. 로컬 Whisper 구현의 출처는 [MLX Whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper)입니다.

현재 도구가 없다고 바로 설치하지 않고, 발견된 경로·version·지원 기능·필요 dependency를 먼저 보고합니다. 설치 범위를 정한 뒤 고정한 dependency와 model만 준비합니다. 외부 유료 전사는 기본 fallback으로 두지 않습니다.

### 렌더 경로의 채택 기준

단일 timeline은 유지하되 Remotion의 성능 적합성은 아직 미검증입니다. 공식 문서도 코드·하드웨어·concurrency에 따른 차이를 설명합니다. [Remotion performance](https://www.remotion.dev/docs/performance/).

- 환경 점검에서 preview 대기 시간, 긴 sample의 렌더 시간, peak memory·임시 디스크 한도, caption 수정 후 재렌더 허용 범위를 먼저 정해 보고서에 기록합니다. 수치를 아직 정하지 못했다면 성능 적합성도 미확정으로 남깁니다.
- 같은 codec·해상도·효과 밀도를 유지하고 길이만 늘린 sample을 비교합니다. 초기 준비 비용과 반복 실행 비용을 구분하고 실제 시간·메모리·디스크를 기록합니다.
- caption 한 곳을 수정한 뒤 preview와 결과를 다시 만드는 시간을 따로 측정합니다. timeline 재사용이 render frame cache나 부분 재렌더를 자동 보장하지는 않습니다.
- 허용 범위를 넘으면 decode·composition·encoding 중 병목을 확인한 뒤 경로를 조정합니다. 렌더 경로를 바꾸더라도 승인된 편집안과 시간 매핑을 보존하고 동일 sample로 다시 검사합니다.

합성 부하 통과는 측정한 구성의 증거입니다. 실제 촬영본의 codec·HDR·VFR·효과 구성이 다르면 확대 전에 해당 조건을 따로 확인합니다.

## 7. 긴 원본과 유연한 러닝타임

### 긴 원본의 검토·재개

1. 허용된 source root에서 inventory를 만들고 hash·길이·stream·회전·색상·촬영 시간의 근거를 기록합니다. 같은 파일명은 동일 source로 간주하지 않습니다.
2. 긴 파일을 도구·resource에 맞는 분석 구간으로 나눕니다. 이 구간 크기는 완성본 길이와 별개입니다. 경계에서 대사·사건이 끊기지 않도록 겹친 범위를 보고 병합합니다.
3. 현재 brief에 맞춰 transcript와 frame 탐색으로 후보를 찾습니다. 대사·시각 변화·현장음의 근거를 구분합니다. 원음을 해석하는 경로가 없다면 그 한계를 남기고 waveform이나 ASR만으로 웃음·감정을 확정하지 않습니다.
4. 후보 주변을 더 촘촘하게 확인하고 observation·해석·source 구간·불확실성을 기록합니다. 한 장의 웃는 얼굴에서 웃긴 사건이나 인과관계를 확정하지 않습니다.
5. 후보가 나오지 않은 구간도 별도 예산으로 재검토합니다. 무대사·변화가 적은 구간·분석 경계를 포함하고, 특정 후보 점수에만 의존하지 않는 시간대별 표본을 더합니다. 대상 구간과 선택 규칙을 기록해 같은 곳만 반복 확인하지 않습니다.
6. 재검토에서 중요한 누락이 발견되면 해당 유형의 인접 구간이나 유사 조건을 더 확인합니다. 확대 범위가 budget을 넘으면 탐색을 중단하고 미검토 범위를 남깁니다. 재검토 표본만으로 전체 누락률을 추정하지 않습니다.
7. source hash·구간·audio track·tool/model version·옵션을 cache key에 포함합니다. 유효한 성공 결과만 재사용합니다. brief를 사용하는 후보 선별에는 brief revision도 연결합니다.
8. `coverage.json`에 metadata·transcript·sampled frames·구간 재생·human review의 실제 근거 종류와 범위를 구분합니다. 후보 없음·미검토·근거 부족·검토 후 제외를 별도로 기록하고 frame sampling을 전체 시청으로 기록하지 않습니다.
9. budget·시간·오류로 중단하면 checkpoint와 미검토 범위를 남깁니다. 다음 세션은 state와 artifact를 검증한 뒤 미완료 범위부터 이어 갑니다.

도구가 연속 재생·원음 확인을 제공하지 못했다면 그 한계를 남깁니다. Claude의 관찰, 전사 model의 출력, 사용자의 실제 시청·청취를 서로 구분합니다. 샘플을 검토한 결과로 전체 촬영분의 선별 완료를 주장하지 않습니다.

**탐색 완료는 사전에 정한 범위와 재검토 절차를 수행했다는 뜻**입니다. 모든 좋은 순간을 찾았다는 뜻은 아닙니다. 예산 소진은 `paused`로 기록하며, 사용자가 부분 범위의 편집을 요청한 경우에는 해당 범위를 brief와 결과에 명시합니다.

### 장면 발견 능력 확인

실제 sample 검증에서는 사람이 중요한 순간과 반드시 남길 맥락을 먼저 표시합니다. 이 정답 목록은 첫 후보 탐색에 제공하지 않고 결과가 나온 뒤 대조합니다. 알고 있는 순간의 timecode를 알려 준 집중 탐색은 근거 확인 검사이며, 스스로 장면을 발견하는 능력의 증거로 쓰지 않습니다.

후보의 유효성, 놓친 중요한 순간, 불필요한 후보, 사용자의 추가 검토량을 함께 기록합니다. 비교 전에 `must_keep`로 지정한 사건이 누락되면 해당 조건의 탐색은 확대 준비가 되지 않은 것으로 봅니다. 원인을 수정한 뒤에는 아직 알려 주지 않은 다른 장면에서도 확인합니다. 나머지 주관적 선호와 허용 누락은 sample 검토에서 정하고, 작은 표본의 결과를 전체 촬영본으로 일반화하지 않습니다.

### Context를 제한하는 재개 방식

- 주 세션은 state·brief·coverage 요약과 현재 작업에 필요한 source 구간만 읽습니다. 전체 transcript와 frame을 매번 대화에 넣지 않습니다.
- source ID·구간·artifact 경로·revision으로 근거를 찾아갑니다. 요약에는 원문 참조를 유지하고 중요한 컷·문구를 결정할 때 해당 원문을 다시 확인합니다.
- 한 번에 읽을 구간·frame 수와 context 사용 범위를 작업 예산에 포함합니다. 한도에 가까워지면 근거와 다음 행동을 저장한 뒤 새 세션에서 재개합니다.
- 재개 검증에서는 새 세션이 특정 장면의 선택 이유·원본 구간·미해결 항목을 저장된 자료만으로 복원하는지 확인합니다.

이 방식으로도 반복 재독이나 context 손실이 병목으로 측정될 때만 Claude Code 내부 subagent를 검토합니다. 도입한다면 source 구간을 읽고 근거 reference를 반환하는 제한된 역할부터 시작하며, 주 세션이 편집 결정과 canonical 출력의 쓰기를 맡습니다. 별도 coding agent나 외부 coordinator는 도입하지 않습니다. Claude Code의 subagent는 별도 context를 사용할 수 있지만 그 자체로 비용·품질 개선을 보장하지는 않습니다. [Claude Code subagents](https://code.claude.com/docs/en/sub-agents).

### 길이와 편수 결정

- 러닝타임은 채택한 이야기와 유효 구간의 합으로 계산합니다.
- 웃음이 필요한 brief에서는 setup → payoff → reaction의 맥락이 전달되는 범위를 남깁니다. 과정·기록 중심이면 해당 이해에 필요한 맥락을 우선합니다.
- 아름다운 장면은 구도·빛·움직임·현장음과 장면 연결을 보고 선별합니다.
- 반복·정보 중복·서사 기여가 낮은 구간은 제외 이유를 기록합니다.
- 필요한 침묵과 감성 구간은 기계적인 silence 제거로 삭제하지 않습니다.
- 사진은 같은 사건과 장소의 이야기를 보완할 때 배치하고, 유지 시간·crop·motion의 이유를 남깁니다.
- 여러 편으로 나누는 안은 이야기의 독립성과 흐름을 근거로 제안합니다. 날짜별 분할은 필수 조건이 아닙니다.
- 결과가 길다는 이유만으로 FAIL 처리하거나 정해진 분량에 맞춰 핵심 사건을 잘라내지 않습니다.

원본 분석의 resource 한도와 결과 영상 길이는 서로 다른 설정으로 유지합니다.

## 8. 데이터 계약, caption, 검증 기준

완성된 편집 엔진의 schema를 먼저 대량 작성하기보다, 합성 sample을 실제로 연결하는 데 필요한 최소 계약부터 확정합니다. 아래 파일은 그 계약의 목표입니다.

| Artifact | 최소 내용 | 필수 검사 |
| --- | --- | --- |
| `brief.json` | `vlog_type`, 주제·이야기·톤·caption/sound 방향·프롬프트 근거·resolved config·취향 revision | 유형 미확정·이전 run 혼입·현재 프롬프트 충돌·재개 시 기본값 자동 변경 |
| `inventory.json` | `source_id`, hash, `kind: video/image`, 실제 metadata, 경로 | 경로 containment·중복 identity·unsupported format. image에 video FPS를 발명하지 않음 |
| `coverage.json` | source 구간·근거 종류·검토/보류 상태·artifact reference·후보 없는 구간의 재검토 이력 | 누락·중복·source 범위·확인 방식·탐색 완료와 예산 중단의 구분 |
| `transcripts/` | source/audio track·원문·timestamp·backend/model·불확실성 | source hash·시간 범위·실제 timestamp 정밀도 |
| `moments.json` | source 구간·관찰·해석·선택 근거·관련 사건 | 대사/시각 근거 연결·인과 추정·앞뒤 맥락 |
| `edit_decisions.json` | 선택/제외·source in/out 또는 image 유지 길이·순서 | 경계·필수 맥락·중복·추정 러닝타임 |
| `timeline.json` | 공통 output FPS·정수 frame 범위·source mapping·canvas·원음/BGM/SFX cue와 gain envelope | 누적 rounding·실제 PTS mapping·의도하지 않은 겹침·output 길이·원음 sync·대사 가림 |
| `captions.json` | cue 종류·근거 reference·출력 frame·style·검토 상태 | timing·대사 의미·가림·읽기·정책 revision |
| `config/media-licenses.json` | asset ID·hash·출처·취득 시점·플랫폼별 이용 조건·claim 관련 근거·credit 문안 | 무료 이용·세 플랫폼 용도·표기 조건·대상 파일 일치. 불명확한 asset은 보류 |
| `audio-credits.md` | 현재 timeline에서 실제 사용한 음원의 설명란용 표기 문안·입력 revision | 누락·교체 후 오래된 표기·미사용 음원 혼입. 무표기 음원만 쓰면 그 사실 기록 |
| `state.json` / `approvals/` | 단계·입력/출력 hash·실패/보류·실제 사용자 승인 근거 | stale 승인·완료 오인·존재하지 않는 결과 참조 |
| `verify/` | 검사·상태·대상 hash·관찰 방법·남은 문제 | 기술 QA와 human review 구분 |

원본 구간은 source seconds로, 출력 구간은 공통 FPS의 `[start_frame, end_frame)`로 구분합니다. VFR proxy를 만들면 실제 source PTS와의 mapping을 유지합니다. cue도 output frame에 연결하고, renderer나 외부 자막 형식에서 필요한 시간 변환은 한 함수에서 처리합니다.

### 결과물의 책임과 변경 영향

`edit_decisions.json`은 source 구간·순서·유지 길이의 편집 결정을 담고, `timeline.json`은 그 결정을 출력 frame으로 변환한 실행 입력입니다. story 문서는 그 이유를 설명합니다. story·편집 결정·timeline을 각각 독립적으로 수정하지 않으며, 컷 변경은 편집 결정에서 시작해 timeline을 다시 계산합니다. renderer는 해당 timeline revision을 참조하는 caption을 사용합니다.

각 결과물에는 `artifact_id`, `revision`, `content_hash`, `depends_on`을 두는 것을 제안합니다. 의존 대상의 ID·revision·hash와 사용한 도구·model·옵션을 연결합니다. 다른 run의 자료를 복사하거나 파일이 존재한다는 이유만으로 최신 결과로 인정하지 않습니다.

| 변경 | 재사용할 수 있는 범위 | 다시 검토하거나 생성할 범위 |
| --- | --- | --- |
| caption 표시 오타 수정, 의미·시간 동일 | source 분석·moments·편집 결정·timeline | 해당 caption, 영향을 받은 preview·가독성 QA·그 결과의 승인 |
| 전사의 부정어·고유명사 등 의미 수정 | source metadata·변경 없는 frame 근거 | 해당 전사를 사용한 moments·caption·선별 판단. 편집 결정까지 바뀌면 timeline도 갱신 |
| brief의 이야기·톤 변경 | 변경 없는 inventory·중립적 전사·frame 추출 결과 | brief를 사용한 후보 선별·moments 해석·story·편집 결정·caption·관련 승인 |
| 프로젝트 기본 취향 변경 | 기존 run 전체 | 새 run 기본값에만 반영. 기존 run은 명시적 적용 요청이 있을 때 위 규칙 사용 |
| source 또는 ASR model·옵션 변경 | 변경과 무관한 source·분석 결과 | 변경된 입력에 의존하는 분석 결과와 그 결과를 사용하는 편집·검증 |
| output FPS·해상도·font·오디오 설정 변경 | source 근거와 변경 없는 편집 의도 | 해당 설정에 의존하는 시간 변환·레이아웃·믹스·render·QA·preview 승인 |
| BGM/SFX 교체·gain·ducking·fade 변경 | 변경 없는 원본 전사·frame 분석·영상 컷 | 해당 audio cue·믹스·음질/청취 QA·preview 승인·사용 음원 credit. 이전 출력의 플랫폼 검사 결과는 새 출력에 이전하지 않음 |
| 사용 음원의 이용 조건·표기 근거 변경 | 원본 분석과 영상 컷 | 해당 asset의 이용 가능 여부와 credit. 교체가 필요하면 관련 믹스·preview도 갱신 |
| 게시 용도·계정 유형·지역 또는 claim 관련 근거 변경 | 변경 없는 원본 분석·영상 컷·믹스 | 해당 이용 가능 여부와 플랫폼 관찰 범위 재검토. 음원 교체가 필요하면 위 교체 규칙 적용 |

변경된 의존 대상부터 영향을 받는 결과를 따라가 `stale`로 표시합니다. 영향 범위를 증명할 수 없는 경우 해당 단계 전체를 재검토하되, 이유를 남깁니다. 재검토 결과 내용이 같아도 새 입력을 확인한 기록을 남겨야 합니다. 기존 사용자 승인을 새 preview나 다른 내용에 자동 이전하지 않습니다.

향후 검증에는 caption 오타·전사 부정어·톤 변경 세 사례와 중간 실패를 포함합니다. 재사용한 결과와 무효화한 결과가 표와 일치하고, 검증되지 않은 partial 출력이 `succeeded`가 되지 않아야 합니다.

### 무료 BGM·효과음의 기본 범위

무료 BGM·효과음의 선곡·배치·혼합·교체는 기본 제작 범위에 포함합니다. 이전 문서의 원음 위주 첫 연결을 확장해, 환경 검증에서도 원음/BGM/SFX가 함께 동작하는지 확인합니다. 실제 음원 확보와 청취는 허용된 제작 단계에서 진행합니다.

무료의 운영 정의는 **개별 음원 이용을 위해 구매나 유료 구독이 필요하지 않은 asset**으로 제안합니다. TikTok·Instagram·YouTube의 영상에 포함해 게시하는 권한을 모두 확인합니다. 향후 수익화를 고려해 상업적 이용도 허용된 음원을 우선하는 것을 제안하며, 실제 계정 유형·게시 지역·수익화·협찬·광고 여부는 제작 brief에서 확인합니다. 일반 게시 권한을 광고 집행 권한으로 확장하지 않습니다. 이 기준은 음원 사용료에 관한 것이며 Claude Code 이용료·장비·저장 공간까지 무료라는 뜻은 아닙니다. 무료 체험 뒤 결제되는 서비스나 출처 불명의 재업로드 음원을 대체재로 넣지 않습니다.

사용자의 추가 답변은 **출처 표기 유무보다 세 플랫폼에서 문제가 생기지 않는 음원을 우선하라는 요구**로 반영합니다. 무표기 우선은 초기 운영 제안이며, 표기 필요 음원을 허용한다는 답변으로 해석하지 않습니다. 후보 확보가 충분하면 별도 질문 없이 무표기 후보로 진행하고, 표기 필요 곡을 선택해야 할 때만 포함 여부를 확인합니다. 출처 표기만으로 이용 권한이 생기거나 자동 claim이 없어지는 것은 아닙니다. [Instagram 저작권 안내](https://www.facebook.com/help/354736791367645/).

### 세 플랫폼 공통 선별 기준

`vlog-me`가 약속할 수 있는 것은 근거를 확인한 선별과 문제 발생 시 교체 절차입니다. **어떤 무료 공급처에도 세 플랫폼의 영구적인 무감지·무claim 보증을 부여하지 않습니다.** 합법적으로 허용된 곡도 자동 claim이 생길 수 있으므로 이용 권한과 감지 결과를 분리합니다. [Pixabay의 자동 claim 안내](https://pixabay.com/service/faq/).

- 곡·효과음별 공식 이용 조건에서 세 플랫폼의 의도한 용도와 편집·동기화 범위를 확인합니다. 한 플랫폼 내 사용 허가만 확인된 asset은 공통 목록에서 보류합니다.
- Content ID 등록 표시, 반복 claim 이력, 별도 채널 등록·whitelist·이의 제기를 전제로 하는 곡은 초기 자동 선곡 대상에서 제외하는 것을 제안합니다. 등록 여부나 관련 이력을 확인할 수 없으면 `unknown`으로 남기고, 검색 결과가 없다는 사실을 무등록 증거로 쓰지 않습니다. 권한 또는 위험 판단 근거가 부족한 후보는 `pending`으로 보류합니다.
- 이용 권한 확인은 `license_status`에, 공급처의 등록·claim 관련 정보와 확인 범위는 `claim_evidence`에, 실제 플랫폼 관찰 결과는 `platform_check`에 따로 기록합니다. `platform_check`는 확인하지 않았으면 `not_checked`이며, 관찰 결과에는 플랫폼·시점·계정/용도·출력 hash를 연결합니다. 어느 하나를 근거로 나머지 상태를 자동 통과시키지 않습니다.
- 공식 확인 절차가 제공되고 업로드가 별도로 허용된 경우에만 실제 출력의 플랫폼 검사 결과를 기록합니다. 한 플랫폼의 검사 결과를 다른 플랫폼에 복사하지 않으며, 검사 당시 문제가 없었다는 결과도 미래의 보증으로 표현하지 않습니다. 세 플랫폼에 공통 자동 사전검사 API가 있다고 가정하지 않습니다.
- 적합한 후보가 없으면 조건을 낮추거나 유료 음원으로 전환하지 않고 부족한 사운드 역할을 보고합니다. 다른 무료 후보 또는 사용자가 확인한 무음·현장음 구성으로 수정합니다.

초기 채택 gate는 다음과 같이 제안합니다. `documented_low_risk`는 공식 공급처·권리자가 해당 asset 또는 그 asset에 적용되는 목록에 대해 Content ID 미등록과 별도 claim 해제·whitelist 불필요를 명시한 근거가 있고, 알려진 등록·claim 정보와 충돌하지 않는 상태입니다. 이는 확인일 기준의 선별 근거이며 세 플랫폼의 무감지 인증이 아닙니다. 무료 license나 검색 결과 부재만으로 이 상태를 부여하지 않습니다.

| 이용·claim 근거 | 실제 플랫폼 검사 | 선곡·로컬 렌더 동작 |
| --- | --- | --- |
| 세 플랫폼 중 하나라도 이용 권한 불명확 | 어떤 상태든 | `pending`. 자동 선곡·preview·최종 렌더에 넣지 않음 |
| 세 플랫폼 권한 확인, claim 근거 `unknown` | `not_checked` 또는 일부 플랫폼 이상 없음 | `pending`. 목록에만 보관. 권한 확인이나 한 번의 검사만으로 채택하지 않음 |
| 알려진 등록·반복 claim·별도 해제 절차 필요 | 어떤 상태든 | 초기 자동 선곡에서 제외. 조건을 바꾸려면 별도 정책 변경 필요 |
| 세 플랫폼 권한 확인, `documented_low_risk`, 표기 조건 충족 | `not_checked` | 선곡·로컬 preview·최종 렌더 가능. 게시 검증은 미실행으로 표시 |
| 위 선별 기준 충족 | 해당 출력에서 문제를 관찰하지 않음 | 확인한 플랫폼·시점·계정·용도·출력 hash의 관찰 결과만 기록 |
| 채택한 asset에서 새 claim·차단·음소거 확인 | 문제 관찰됨 | 해당 asset 사용을 보류하고 교체·재검증. 다른 플랫폼도 자동 통과시키지 않음 |

Claude Code는 연결한 공식 근거가 위 조건을 충족하는지 확인해 선별 상태를 기록하고 validator는 필수 근거·hash·상태의 일치를 검사하도록 설계합니다. 사람의 취향 승인으로 `unknown`을 덮어쓰지 않습니다. 이 엄격한 초기 기준을 충족하는 무료 곡이 실제로 얼마나 있는지는 아직 확인하지 않았으며, 후보가 0개일 수도 있습니다. 공급처 추천은 개별 asset의 채택을 뜻하지 않습니다.

촬영 원음도 검토 대상입니다. 카페·매장·TV·공연 음악이 녹음된 구간은 별도 BGM을 넣었다고 해결되지 않습니다. 해당 구간과 청취 근거를 기록하고, 이용 근거가 없으면 원음 제거·대체·대사 보존 편집의 영향을 preview로 확인합니다. ASR이나 음악 탐지만으로 권리 검토 완료를 선언하지 않습니다. 대사를 훼손하는 자동 음소거도 적용하지 않습니다. [Instagram의 녹음된 음악 관련 안내](https://www.facebook.com/help/354736791367645/).

### 우선 검토할 무료 음원 공급처

다음은 2026-10-18 확인한 서비스의 공식 안내를 바탕으로 한 추천입니다. 개별 곡·효과음은 아직 선택하거나 내려받지 않았습니다. 실제 등록 시 asset 페이지와 해당 이용 조건을 다시 확인합니다.

| 공급처 | 사용 위치 | 확인할 조건 |
| --- | --- | --- |
| [Mixkit Music](https://mixkit.co/free-stock-music/) / [Sound Effects](https://mixkit.co/free-sound-effects/) | 세 플랫폼 공통 이용 조건을 먼저 검토할 후보 | Music·SFX의 각 약관은 web/social media 이용을 허용함. 개별 asset과 세부 제한을 대조. Music 약관 자체에 claim 발생 시 안내가 있어 무claim 보증으로 추천하지 않음. [Music license](https://mixkit.co/license/modal/musicFree/), [SFX license](https://mixkit.co/license/modal/sfxFree/) |
| [YouTube Audio Library](https://support.google.com/youtube/answer/3376882?hl=en) | 개별 license가 세 플랫폼 조건을 충족할 때만 공통 후보 | YouTube 공식 안내의 수익화·Content ID 설명을 다른 플랫폼에 확대하지 않음. Studio의 asset별 license에서 외부 사용 조건을 추가 확인 |
| [Pixabay Audio](https://pixabay.com/service/license-summary/) | 초기 자동 선곡의 기본 목록에서는 보류 | 공식 FAQ가 Content ID 등록 곡과 합법적 사용에도 생길 수 있는 claim을 설명함. 추후 개별 후보의 이용·등록 근거를 확인한 경우에만 같은 기준으로 재검토. [Pixabay FAQ](https://pixabay.com/service/faq/) |

TikTok CML이나 Instagram 앱 내 음악·Meta Sound Collection도 한 플랫폼의 안내만으로 공통 목록에 넣지 않습니다. TikTok은 브랜드·제품·서비스 홍보에서 CML 밖 음악을 쓰면 필요한 권리를 확보해야 한다고 안내하며, Instagram의 일반 licensed music library는 개인적·비상업적 사용을 대상으로 합니다. 플랫폼 내 사용 범위와 외부 편집본 재사용 권한을 별도로 대조합니다. [TikTok music use](https://support.tiktok.com/en/business-and-creator/creator-and-business-accounts/commercial-use-of-music-on-tiktok?lang=en), [Instagram music library](https://www.facebook.com/help/instagram/402084904469945).

무료 이용 조건과 플랫폼의 자동 권리 식별 결과는 따로 기록합니다. 공급처 이름이나 “no copyright”라는 제목만으로 claim이 없을 것이라고 보장하지 않습니다. 등록 근거가 없거나 조건이 불명확하면 해당 asset을 사용 목록에서 보류합니다.

초기 운영은 공식 경로에서 확보한 작은 로컬 목록을 재사용합니다. 서비스 로그인과 자동 다운로드 경로는 아직 검증하지 않았으며, 비공식 API나 대량 scraping을 전제로 삼지 않습니다. 사용자가 직접 가져온 파일도 출처·이용 근거를 함께 등록하면 같은 workflow를 사용할 수 있습니다. 현재 문서 수정에서는 로그인·다운로드·결제·업로드를 수행하지 않습니다.

### 선곡·배치·믹싱 절차

1. brief의 유형·톤과 채택된 장면을 보고 `story.md`에 사운드의 역할을 정리합니다. 도입·이동·과정·감정 전환·웃음·마무리 등 사건 단위로 음악을 고르며, 매 컷마다 곡을 바꾸지 않습니다.
2. 로컬 목록에서 분위기·에너지·길이·보컬 유무·사용 이력을 보고 후보를 좁힙니다. 대사와 경쟁하는 보컬, 같은 효과음의 과도한 반복, 반전보다 이른 강조음을 검토합니다. 후보 수와 탐색 범위는 작업 예산에 포함합니다.
3. 원음·현장음·BGM·SFX의 역할을 나눕니다. 대사 중에는 BGM을 낮추는 ducking을 적용하고, 장면 전환에는 필요한 fade와 연결을 둡니다. 음악을 빼고 현장음이나 쉼을 남기는 선택도 사운드 설계에 포함합니다.
4. 실제로 없었던 웃음·충돌·환경음을 사실처럼 들리게 만들지 않습니다. 추가 SFX는 편집적 강조인지 재현음인지 이유를 기록합니다. 현장음으로 등록한 원음과 구분합니다.
5. 선택한 cue를 `timeline.json`의 audio 항목에 넣습니다. `cue_id`, 추가 음원의 `asset_id` 또는 원음의 source ID·`audio_track` stream index, 역할, 사건 reference, source trim, output frame, `gain_db` envelope, fade·loop 여부, 선택 이유를 연결합니다. 추가 음원에는 license revision을 연결합니다. 원음은 영상과 같은 source/output mapping을 쓰며 복수 track을 임의로 모두 혼합하지 않습니다. 별도 master audio timeline은 만들지 않습니다.
6. 충분한 곡 길이와 사용 조건이 있는지 확인합니다. 반복 재생은 연결부를 검토하고, 확인되지 않은 remix·속도/피치 변형을 기본 처리로 사용하지 않습니다. source에 track이 없으면 원음은 무음으로 처리하되 BGM/SFX layer는 별도로 유지합니다.
7. preview를 측정하고 청취한 뒤 사용한 asset만으로 `audio-credits.md`를 갱신합니다. 부적합한 곡은 해당 cue만 교체하고 원본 전사를 다시 실행하지 않습니다. 업로드 후 claim 대응이 필요해도 자동 이의 제기나 외부 연락은 하지 않습니다.

`media-licenses.json`은 asset ID·hash·공급처/asset URL·제작자·license 이름/URL·확인일·취득일·무료 이용 근거·플랫폼별 허용 용도·attribution 요구와 원문 문안·claim 관련 근거 경로를 보존합니다. 플랫폼 관찰 결과는 `verify/`에 두고 같은 asset·출력 hash를 참조합니다. duration·mood·energy·vocal 여부 같은 선곡 metadata는 추정값이면 그렇게 표시합니다. 파일은 `assets/audio/` 또는 허용된 외부 asset root에 두고 등록된 hash와 대조합니다. 아직 선별 기준을 충족하지 못한 asset은 `pending`으로 남겨 renderer가 선택하지 않도록 합니다. 공통 선별 기준을 충족한 asset의 로컬 preview는 가능하지만, 플랫폼 검사를 하지 않은 상태를 게시 검증 완료로 표시하지 않습니다.

실행할 믹스는 각 audio cue가 한 번만 합산되도록 합니다. 같은 효과음을 여러 장면에 쓰는 경우에는 서로 다른 cue ID로 기록합니다. FFmpeg로 미리 만든 믹스를 입력으로 사용한다면 구성 원음과 cue를 renderer에서 다시 더하지 않습니다. ASR은 원본 음성에 수행하며 BGM/SFX를 추가한 결과로 전사 cache를 교체하지 않습니다.

### 사운드 완료 기준

- **취향:** 같은 영상 컷과 caption을 유지한 비교에서 BGM·효과음의 밀도·종류가 원하는 분위기를 만드는지 사용자가 청취합니다. “풍부함”을 곡 수·효과음 수·큰 음량으로 대신 판정하지 않습니다.
- **명료도:** 중요한 대사·현장음이 들리고, ducking의 급격한 출렁임·효과음 충격·반복 피로가 없는지 확인합니다. 파형과 loudness 수치만으로 청취 품질을 통과 처리하지 않습니다. 도구가 실제 오디오 내용을 확인하지 못했다면 청취 완료로 기록하지 않습니다.
- **기술:** source trim·sync·중복 원음·fade/loop 경계·누락 파일·sample rate 변환을 확인합니다. 최종 인코딩 결과의 loudness·true peak·clipping을 측정하며 목표값은 sample에서 정한 출력 profile에 기록합니다. 특정 LUFS 숫자를 YouTube 업로드 합격 기준으로 단정하지 않습니다.
- **이용 조건:** 실제 사용 asset의 hash·세 플랫폼 이용 근거·attribution 조건과 credit 목록이 일치해야 합니다. 원음에 포함된 제3자 음악의 미해결 구간도 보고합니다. 등록·문서 검사가 실제 TikTok·Instagram·YouTube의 업로드·자동 감지 결과를 검증한 것은 아닙니다.
- **실패 처리:** 음원 접근·이용 조건·믹스 검사가 실패하면 해당 cue를 보류합니다. 임의의 유료 곡으로 바꾸거나 조용히 누락한 결과를 완성본으로 표시하지 않습니다. 사용자가 확인한 대체 곡 또는 의도적인 무음으로 바꾸면 revision과 preview를 갱신합니다.

### Caption 규칙과 예능형 선택

기본 대사 자막·예능형 강조·절제된 표시 중 현재 brief의 방향을 사용합니다. 아래 예능형 규칙은 해당 스타일을 선택했을 때 적용합니다.

- 실제 발화는 `dialogue`로 기록하고 원문 근거를 연결합니다.
- 상황을 해석한 편집자 코멘트는 `editorial`로 기록합니다. 인물의 실제 발언이나 속마음으로 바꾸지 않습니다.
- 일반 대사는 읽기 쉬운 기본 스타일을 사용합니다.
- 웃음 포인트에는 필요한 cue만 강조하고 반전보다 먼저 결말을 공개하지 않습니다.
- 감성 구간은 화면과 현장음을 감상할 여유를 두되 필수 대사의 접근성을 임의로 제거하지 않습니다.
- 부정어·가격·고유명사·겹말이 불명확하면 원음 확인 항목으로 남깁니다.
- 얼굴·표정·손동작·중요 피사체와의 겹침은 실제 frame에서 확인합니다.
- font·음원·SFX는 사용 권한을 확인한 asset만 사용합니다. 근거가 없으면 render readiness를 보류합니다.

첫 synthetic fixture에는 지원하는 영상·사진·audio track 없는 source와 명시적으로 거부할 입력을 포함합니다. 세로 영상·HDR/VFR 등 지원 범위를 확장할 때 해당 fixture를 추가합니다. 원본 색상·회전·혼합 canvas를 출력 tag만 보고 정상으로 판정하지 않습니다. 오디오도 decode·경계·sync·측정과 사람의 청취를 나눠 확인합니다.

## 9. 실제 환경 구축 순서와 완료 기준

이 표는 **다음 환경 구성 단계의 계획**입니다. 지금 실행한 작업 목록이 아닙니다. 기존 기능과 새 구현의 경계를 정한 뒤 최소 연결을 만들고, 실제 sample 확인 후 촬영본 규모와 지원 format을 넓힙니다.

| 단계 | 작업 | 산출물·완료 기준 |
| --- | --- | --- |
| 1. 범위·환경 점검 | 도구·디스크·기존 Skill·권한과 기능별 제공 범위 확인 | 지원 format·연결 코드·새 구현 범위·resource 기준을 `reports/setup-report.md`에 기록 |
| 2. 최소 harness | `CLAUDE.md`, 선택한 설정·revision·상태·경로 규칙 구성 | 새 세션이 현재 범위와 다음 행동을 저장된 자료에서 복원 |
| 3. Skills 구성 | 공식 rendering 지침부터 연결. Watch는 통합 조건 충족 시 선택 | 실제 로딩·이름 충돌·쓰기 위치·backend 확인. Custom Skill은 gap이 확인될 때만 추가 |
| 4. 합성 연결 | 제한된 source·편집안·테스트용 오디오로 단일 timeline 구성 | 영상/사진/caption·원음/BGM/SFX 배치·fade·ducking 연결. 실제 선곡 품질은 미검증 |
| 5. 수정·실패·재개 | 작은 수정, 음원 교체·미등록 asset, 중간 실패, 새 세션 재개 | 필요한 결과만 무효화, credit 갱신, partial 성공 오인 차단, 원본·기존 결과 보존 |
| 6. 부하 확인 | 같은 조건에서 길이를 늘리고 caption 수정 후 재렌더 | 시간·메모리·디스크·대기 시간을 사전에 정한 한도와 대조 |
| 7. 환경 보고 | 연결 성공과 실제 제작 품질을 분리 | 실행 가능한 명령·지원 범위·미확인 항목·다음 허용 단계 기록 |

### 실제 sample로 취향과 장면 발견 확인

아래는 실제 원본 처리가 허용된 다음 단계의 절차입니다. 환경 구축이나 합성 검증 성공만으로 자동 실행하지 않습니다.

1. 프롬프트에서 유형·핵심 이야기·톤을 정하고, 허용된 원본 및 Claude Code에 제공할 자료 범위를 brief에 기록합니다.
2. 현재 brief를 대표하는 대화·동작·무대사 장면·사진을 필요한 만큼 선택합니다. sample 길이는 검증할 내용에 따라 정하며 본편 분량을 제한하지 않습니다.
3. 같은 장면으로 caption 밀도·강조 방식·컷 호흡 중 한 요소를 달리한 소수의 preview를 비교합니다. 사운드 비교에서는 영상 컷과 caption을 고정하고 BGM·SFX의 종류 또는 밀도를 바꿉니다. 모든 유형에 예능 자막·과장된 효과음을 강제하지 않습니다. 사용자가 선호한 안과 이유, 피하고 싶은 표현과 소리를 기록합니다.
4. 선택한 원칙을 아직 비교하지 않은 다른 장면에 적용합니다. 첫 예시에서만 통하면 취향 확인을 완료로 처리하지 않고 적용 조건을 좁히거나 지침을 보완합니다.
5. 7절의 정답 목록을 가린 장면 탐색도 별도로 평가합니다. 보기 좋은 preview와 좋은 장면을 스스로 찾는 능력을 하나의 결과로 합치지 않습니다.

취향 결과는 우선 해당 run의 brief에 보존합니다. 반복 사용할 예시·원칙은 `editorial-guide.md`에 적용 유형·톤·caption 스타일과 함께 revision으로 기록하고, 사용자가 선택한 경우에만 다른 run에 적용합니다. 첫 단계부터 취향 전용 Skill을 만들지 않습니다.

### 전체 분석과 최종 결과로 확대

1. 실제 sample에서 확인한 지원 조건·취향·탐색 한계를 바탕으로 분석 범위를 넓힙니다. 새 format은 별도 검증하거나 보류합니다.
2. 후보가 없는 구간의 재검토까지 수행한 범위에서 story·편집안·예상 러닝타임·남은 미검토 범위를 제시해 사용자가 확인합니다.
3. 채택된 편집안과 sound 방향에 따라 등록한 무료 음원을 선곡·배치합니다. 본편 preview와 기술 QA를 만들고 사용자가 실제로 시청·청취합니다.
4. 확인한 현재 preview·설정·음원 목록을 기준으로 최종 렌더하고 해당 timeline의 credit 문안을 함께 전달합니다.

이는 사용자의 창작 판단을 확인하기 위한 제안입니다. 이미 허용한 단계의 일반적인 도구 호출마다 승인을 반복하지 않습니다. 전사·편집안·style·출력 설정이 바뀌면 관련 승인과 cache의 유효성을 다시 확인합니다. 세 플랫폼의 upload와 게시 검증은 별도 작업입니다.

### 준비 상태의 구분

다음은 향후 보고할 상태의 정의이며 현재의 통과 결과가 아닙니다. 각 상태에 대상 source·format·toolchain·설정 revision을 연결합니다.

| 상태 | 통과에 필요한 근거 | 증명하지 않는 것 |
| --- | --- | --- |
| `synthetic_pipeline_ready` | 합성 preview·원음/BGM/SFX 혼합·수정·실패 처리·재개 성공 | 실제 한국어 전사, HDR 색감, 선곡·청취 품질 |
| `real_media_validated` | 허용된 실제 sample의 decode·시간 매핑·원음/전사·최종 믹스 측정 | 모든 format·전체 촬영본·실제 Content ID 결과 |
| `editorial_calibrated` | 같은 장면의 영상·사운드 비교와 다른 장면의 적용 결과를 사용자가 확인 | 다른 유형·다른 취향에 대한 자동 승인 |
| `selection_evaluated` | 숨긴 중요 순간 목록과 후보의 대조, 누락·추가 검토량 기록 | 전체 영상의 모든 좋은 순간 발견 |
| `scale_validated` | 선언한 구성과 길이에서 렌더·재렌더·resource 기준 충족 | 측정하지 않은 해상도·길이·효과의 성능 |

실제 촬영본으로 확대하려면 관련 상태와 남은 제한을 함께 검토합니다. 기술적으로 렌더되었다는 이유로 취향·선별 평가를 통과 처리하지 않습니다.

### 구축 후 준비해야 할 검증 명령

아래는 목표 인터페이스입니다. **현재 파일과 package가 없어 이번에는 `NOT_RUN`이며 그대로 실행할 수 있는 상태가 아닙니다.** 구축 단계에서 구현한 명령과 실제 결과로 갱신합니다. 모든 명령의 기준 경로는 `/Users/soom.kang/Desktop/work/2.services/vlog-me`입니다.

```sh
./scripts/doctor.sh
python3 scripts/inventory.py --help
python3 scripts/validate.py --fixtures tests/fixtures
npm --prefix renderer run lint
npm --prefix renderer run typecheck
npm --prefix renderer test
./scripts/smoke-render.sh
```

`inventory.py --help`는 CLI 안내 확인이며 실제 inventory 생성의 성공을 증명하지 않습니다. 구축 시에는 허용된 synthetic 입력으로 실제 수집·실패 사례도 확인해야 합니다. 위 명령에 대한 exit code와 결과 경로는 구현 계획에서 확정합니다.

검증 범위는 Claude session의 지침·Skill 로딩, JSON 참조, source/output 시간, 사진 유지 길이, caption 의미·가림·읽기, decode·오디오 sync·혼합, cache·resume, 승인 무효화를 포함합니다. 오디오 fixture에는 원음+BGM+SFX 동시 재생, 원음 없는 source, fade/ducking, 중복 원음 방지, `pending` license, 파일 교체, 필요한 credit 누락을 포함합니다. setup에서는 합성 미디어만 사용하며 한국어 전사 정확도·취향 적합성·실제 HDR 색감·실제 음원 청취는 별도 sample 검사로 남깁니다.

음원 정책 fixture에는 한 플랫폼만 허용된 asset, 알려진 Content ID 등록, 근거 부족, `not_checked`, 계정·용도 변경, 교체 전 출력의 오래된 검사 결과를 포함합니다. 이 검사는 기록과 차단 규칙만 확인하며 실제 플랫폼의 감지 동작을 재현하거나 인증하지 않습니다.

## 10. 주요 가정의 반증과 작은 검증

아래는 적대적 검토에서 드러난 가정을 확인할 계획입니다. 미디어 실험은 아직 실행하지 않았습니다. 이미 문서와 source 대조로 확인한 Watch의 저장 위치 차이도 실제 설치 영향과 구분합니다.

| 가정 | 근거 있는 위험 | 가장 작은 유용한 확인 | 판단 기준·한계 |
| --- | --- | --- | --- |
| 기존 Skills로 대부분의 제작이 바로 연결됨 | 지침과 실행 기능 사이에 composition·변환·상태 연결 코드가 필요 | 3절의 제공 범위를 확인하고 제한된 합성 입력의 전체 연결 실행 | 미지원 부분과 새 구현 범위가 드러나야 함. 실제 편집 품질은 별도 |
| 첫 후보 탐색만으로 중요한 장면을 찾음 | 후보가 없는 구간은 후속 정밀 검토에서도 빠질 수 있음 | 사람의 중요 순간 목록을 가린 탐색과 후보 없는 구간 재검토, 이후 정답 대조 | must_keep 누락 시 해당 조건의 확대 보류. timecode를 알려 준 재탐색 성공은 발견 능력으로 계산하지 않음 |
| 취향을 설명하면 원하는 편집으로 재현됨 | 같은 추상어로 다른 caption·호흡을 만들 수 있음 | 같은 장면의 변형 비교 후 다른 장면에 선택 원칙 적용 | 사용자 선택 이유와 적용 범위를 기록. 첫 장면만 통과하면 확인 미완료 |
| project scope Skill 설치가 runtime도 격리함 | Watch 기본 setup·cache는 사용자 홈을 사용 | 채택 ref의 쓰기 경로 확인, 허용된 setup의 변경 전후 대조 | project-local 지원 또는 명시적으로 선택한 공유 범위가 필요. 미충족이면 Watch 채택 보류 |
| Remotion 단일 timeline이 긴 본편에도 적합함 | 디코딩·메모리·디스크·재렌더 비용은 아직 측정하지 않음 | 조건을 유지하고 길이를 늘린 부하 sample 및 caption 한 곳 수정 후 재렌더 | 사전 정의한 시간·resource 한도와 대조. 측정하지 않은 실제 source에는 확대 해석 금지 |
| 짧은 Skill 지침만으로 원본을 보호함 | 지침과 Bash 문자열 규칙은 모든 쓰기 경로를 통제하지 못함 | synthetic source/output alias·traversal·기존 결과에 대한 helper/hook 실패 사례 | 차단된 경로만 증명. OS 수준 격리로 표현하지 않음 |
| 변경·재개 시 필요한 작업만 다시 수행함 | 의존 관계가 빠지면 stale 결과를 재사용하거나 모든 작업을 반복 | caption 오타·전사 부정어·톤 변경 및 부분 출력에서 재개 | 8절의 재사용·무효화 범위 일치. 프로젝트 기본값 변경은 기존 run에 자동 적용하지 않음 |
| 순차 실행이면 긴 촬영본의 context도 관리됨 | frame·전사를 계속 쌓으면 근거를 잃거나 반복해서 읽을 수 있음 | 새 세션이 state와 참조 자료로 지정 장면의 이유·원본 구간·미해결 항목 복원 | 복원 실패나 반복 비용을 기록. 필요한 구간 재조회부터 개선하며 subagent는 측정 후 검토 |
| 같은 harness가 유형과 톤에 맞게 작동함 | 이전 run의 여행 설정이나 예능 스타일을 다음 일상·과정형 제작에 그대로 적용할 수 있음 | 여행·일상·기타 프롬프트를 각각 brief로 정리하고 새 run·유형 미지정·중간 톤 변경을 문서 사례로 대조 | 명시한 프롬프트 우선, 실제 제작의 유형 미정은 확인 필요, story/caption의 변경 영향 기록. 아직 runtime 실험은 아님 |
| 고정 길이를 없애면 좋은 이야기만 남음 | 길이 자유와 서사 품질은 별개 | story draft의 필수 사건·중복·제외 이유를 사람이 확인 | 러닝타임이 짧거나 길다는 사실만으로 성공/실패 판정 금지 |

### 새 프로젝트·무료 사운드 요구에 대한 적대적 검토

| 우선순위 | 실패할 수 있는 가정·확인된 충돌 | 문서에 반영한 수정 | 이후 확인할 가장 작은 사례 |
| --- | --- | --- | --- |
| 높음 | 새 harness를 구성하려면 기존 Skills도 모두 새로 만들어야 함 | 프로젝트명·새 구조의 소유 범위를 명시하고 기존 Skills 우선 원칙 유지 | 구축 목록에서 기존 기능·연결 코드·새 구현의 중복 확인 |
| 높음 | 원음 위주 최소 구성만으로 풍부한 BGM/SFX 요구를 충족함 | 기본 composition과 제작 절차에 선곡·배치·ducking·교체를 포함 | 합성 다중 track 연결 후 실제 무료 음원을 넣은 sample 청취 |
| 높음 | 무료 다운로드나 한 플랫폼의 허가면 세 플랫폼에서도 문제가 없음 | asset별 무료 이용·세 플랫폼 용도·표기·hash·출처 기록. 권한과 감지 결과 분리 | YouTube만 허용된 asset과 `not_checked`를 공통 게시 검증 완료로 처리하지 않는지 확인 |
| 높음 | 등록 표시가 없거나 license가 있으면 절대 claim이 없음 | 무감지 보증 제거, 알려진 등록·claim 후보 제외, 불확실한 후보 보류·교체 경로 | Content ID 등록·근거 불명·교체 후 오래된 QA 사례 확인 |
| 높음 | 추가 BGM만 적합하면 영상 전체 음원 문제도 해결됨 | 원음에 녹음된 카페·TV·공연 음악의 확인과 대사 보존 대안 추가 | 원음에 음악이 섞인 sample을 감지/전사 성공만으로 통과시키지 않는지 확인 |
| 높음 | 소리를 많이 넣을수록 재미와 감성이 좋아짐 | 사건별 역할·현장음·쉼을 포함하고 수량 목표 제외 | 같은 영상에 사운드만 달리해 대사 명료도·과장·반복 피로를 비교 |
| 높음 | source별 volume만 낮추면 믹스가 안전함 | 최종 혼합·인코딩 결과의 측정과 사람 청취를 분리 | 동시 SFX·대사 구간·loop 경계·중복 원음 사례 확인 |
| 중간 | 음원만 바꾸면 나머지 결과는 모두 유효함 | audio cue·preview·QA·credit의 의존 revision 갱신 | 표기 필요 곡을 다른 곡으로 바꾼 뒤 오래된 credit·승인이 남지 않는지 확인 |
| 중간 | 웹 음원을 항상 자동으로 확보할 수 있음 | 작은 로컬 목록 우선, 공식 접근·수동 등록 경로 포함 | 로그인 불가·검색 실패 때 사용 가능한 로컬 후보 또는 보류를 보고하는지 확인 |
| 중간 | 기술 QA만으로 사운드 취향을 검증함 | 선곡·타이밍·청취 결과를 실제 sample에서 별도로 기록 | waveform 검사만 성공하고 청취가 없는 경우 완료 판정 금지 |

위 항목 중 새 요구와 이전 문서의 원음 위주 범위 충돌은 문서 대조로 확인했습니다. 무료 이용·표기·매체 제한은 연결한 공식 안내에 근거합니다. 실제 음원의 적합성, 믹스 품질, 자동 확보 가능성은 아직 검증하지 않았습니다.

## 11. 설계 검토와 현재 검증 상태

이전 문서에서 정리한 여섯 개선안을 유지하고, 이번에는 `vlog-me`의 새 harness + Skills 구성과 무료 BGM·효과음 활용 요구를 추가했습니다. 이전 버전의 독립 검토 결과를 수정본의 검증 결과로 재사용하지 않습니다. 무료 음원·사운드 관련 변경과 적대적 검토는 8–10절에 정리했습니다.

| 검토에서 지적한 항목 | 반영 위치 |
| --- | --- |
| 첫 탐색에서 누락한 장면의 재발견 경로 | 7절: 후보 없는 구간 재검토, 정답 목록을 가린 발견 능력 평가 |
| 취향 기록과 취향 재현의 차이 | 9절: 같은 장면 비교, 다른 장면 적용, 적용 범위·revision 기록 |
| Watch의 project scope와 사용자 홈 runtime 차이 | 4절: 쓰기 경로·backend 검토, 미충족 시 대안 사용 |
| 변경·재개의 영향 범위 | 5·8절: run 설정 보존, 의존 revision과 변경별 무효화 |
| 최소 harness의 자체 개발 범위 확대 | 3·6·9절: 제공 기능 구분, 최소 연결, 렌더·재렌더 부하 기준 |
| Claude Code 단독과 단일 context 고정의 혼동 | 1·7절: 범위별 근거 조회, 새 세션 복원, 측정 후 내부 subagent 검토 |

### 설계 작성 당시 관찰 — 구축 전

2026-10-18 확인한 `vlog-me`에는 이 문서만 있으며 Git repository가 아닙니다. `CLAUDE.md`, `.claude/skills/`, renderer, toolchain, 실행 script는 아직 없습니다.

이전 문서 작성 때의 shell PATH 검사에서는 Claude Code·FFmpeg·ffprobe·Python·uv 경로를 찾았고 Node·npm·ExifTool은 찾지 못했습니다. 이번 수정에서는 설치 상태를 다시 점검하지 않았습니다. machine 전체의 미설치를 뜻하지 않으며, version·의존성·실행 성공의 증거도 아닙니다. 실제 구축 전에 재확인해야 합니다.

### 문서 수정 당시 검증

- 문서 구조·JSON·로컬 참조·요구사항 대조: `PASS`. 12개 주 절·code fence·JSON 예시·첨부 경로를 검사했고, 기존 설정값과 이번 추가 요구의 일치를 확인했습니다. 실행 구현의 통과 결과가 아닙니다.
- 독립 cold review·builder 확인: 작성 맥락을 받지 않은 reviewer가 첫 사운드 수정본 1–621행을 읽고 `self_contained`로 판정했습니다. 사용자 답변으로 플랫폼 범위가 바뀐 뒤 같은 reviewer가 1–642행을 추가 검토해 `gaps_present`로 판정했으며, claim 근거 `unknown`인 asset의 채택 조건 1건을 지적했습니다. 추가 검토는 새 최초 cold read가 아닙니다.
- 지적 사항의 수정: 8절에 상태별 채택 gate와 최소 근거·판단 책임을 추가했습니다. 작성 세션에서 권한 불명·claim 근거 불명·알려진 등록·이용 근거 충족/플랫폼 미검사·새 claim 사례를 대조했습니다. 이는 문서 검토이며 수정 후의 별도 독립 통과나 runtime 검증으로 표현하지 않습니다.
- 실제 Claude Code Skill 로딩·hook·합성 render·ASR·typecheck/tests: `NOT_RUN`. 이번에는 실행 자산을 만들지 않았습니다.
- 원본 미디어 접근·음원 다운로드·미디어 provider 호출·model 다운로드·Git 초기화·commit·push·외부 활성화: 수행하지 않았습니다.
- 변경 범위: 이 설계 문서 1개. 다른 프로젝트와 전역 설치·설정은 변경하지 않았습니다.

### 확인이 필요한 사항

하드웨어·메모리·총 촬영본 규모·원본 format·보유 font/음원 권한은 아직 확인하지 않았습니다. 이 정보는 설치·전사 model·resource 한도를 확정할 때 필요하며, 문서 재작성 자체를 막는 입력은 아닙니다.

TikTok·Instagram·YouTube에서 문제없는 음원을 원한다는 요구는 확정했습니다. 실제 곡과 자동 감지 결과는 아직 확인하지 않았습니다. 상업적 이용 허용 음원 우선·무표기 우선·알려진 등록 곡 제외·`rich_contextual`은 이 요구를 구현하기 위한 설계 제안입니다. 실제 계정·게시 용도, 필요한 경우의 표기 음원 포함 여부, 음악 장르·SFX 밀도는 제작 brief와 sample 비교에서 정합니다.

가로 16:9·SDR BT.709·H.264/AAC는 기본 납품안으로 제안하되 원본 확인 후 output 해상도·FPS·HDR 정책을 확정합니다. 무조건 1080p나 특정 FPS로 변환하지 않습니다. 비용·처리 시간·한국어 정확도·영상미 개선 효과는 아직 측정하지 않았습니다.

## 12. 사용한 자료와 유지보수

첨부 자료:

- A: [Codex와 Claude 역할 분리 제안](</Users/soom.kang/.codex/attachments/12a79394-f350-4cc9-ba34-3e8f20e0c5bc/붙여넣은 텍스트.txt>). 역할 분담은 제외하고 원본 보호·합성 검증·재개 조건을 참고했습니다.
- B: [사진·영상 통합 자동편집 제안](</Users/soom.kang/.codex/attachments/62a6b29d-ecb7-46d6-8013-15d11f4bbaac/붙여넣은 텍스트.txt>). 혼합 미디어·사진의 서사 역할·음성 우선 믹싱을 참고했습니다.
- C: [Claude Code Skills 조합 제안](</Users/soom.kang/.codex/attachments/54b10c60-d62e-4a65-8ad5-fe133e79dbfd/붙여넣은 텍스트.txt>). 구간별 탐색과 story/caption Skill 분리를 중심으로 반영했습니다.

공식 문서와 공개 source는 관련 주장 옆에 연결했습니다. 일반적인 도구 선택은 권장안이며 사용자 환경의 설치 성공으로 표현하지 않았습니다.

이 문서는 기존 설계안을 대체합니다. 구축 후에는 설치한 Skill과 도구의 ref·version·검증 결과를 프로젝트에 남기고 schema·model·renderer·권한 정책이 바뀔 때 관련 sample을 다시 검증합니다. 설계 검토 요청은 새 harness + Skills 구조, 무료 BGM·효과음·세 플랫폼 공통 선별 기준과 적대적 검토를 문서에 반영하는 범위였습니다. 이후 환경 구축도 허용되었으며 실제 결과는 구축 보고서에서 관리합니다. Claude Code 단독·기존 Skills 우선·제작별 프롬프트·유연한 러닝타임을 유지하고, 실제 원본 처리와 음원 다운로드는 계속 제외합니다.
