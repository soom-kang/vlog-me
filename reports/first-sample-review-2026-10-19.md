# 첫 실제 sample: 후보 리뷰까지 (2026-10-19)

## 요청 범위

- 원본: `sources/vietnam-20260527/` (이 폴더만 읽음)
- 클립 2–3개와 사진 몇 장, 재미 60 · 감성 40, 자막 예능 80 · 감성 20, 소소한 재미 위주
- 후보 리뷰 페이지까지만 진행. 렌더·음원 다운로드는 하지 않음

## 바꾼 설정

- `config/project.json`: `phase: production`, `source_roots: ["sources/vietnam-20260527"]`, `asr_model: ggml-large-v3-turbo.bin`. `audio_search`·`audio_downloads`·`production_render`·`upload`는 `false`
- `.claude/settings.json`: `Read(sources/**)`, `Bash(* sources/*)`, `Bash(* ./sources/*)` deny만 제거. `Edit/Write(sources/**)` deny와 `protect_sources.py` hook은 유지
- 합성 검증으로 돌아갈 때는 두 파일을 git의 setup 설정으로 되돌림

## run: prod-20261019-075246-e19437c2

| 단계 | 결과 | 근거 |
| --- | --- | --- |
| ingest | PASS | 영상 30·사진 298, skipped 0, HDR·VFR 0 (`sources.json`) |
| analyze 1차 | FAIL | v012(0.7초) contact sheet에서 ffmpeg MJPEG 인코더 실패. `analysis.failed-20261019-075815/` 보존 |
| analyze 2차 | PASS | `scripts/analyze.py` 수정 후 재실행 (`analysis/index.md`) |
| 후보 리뷰 | PASS | `review/v3/index.html` (v1·v2 보존) |
| 선택·조립·렌더 | NOT_RUN | 요청 범위 밖 |

## 코드 변경

- `scripts/analyze.py:151`: contact sheet 필터에 `eof_action=pass`. 1초 미만 클립은 `fps=1/2`가 프레임을 하나도 내보내지 않아 인코더가 열리지 못했음. 긴 클립은 2초 간격 마지막 프레임 1장만 추가(시간 대응 유지)
- 테스트: `tests/test_analyze.py` PASS. 전체 112개는 setup config 사본에서 PASS(skip 6). 현재 production config에서는 합성 scope 전제 테스트 16개가 scope 거부로 FAIL(예상된 동작)

## 후보 (13개 · 클립 3개 + 사진 5장)

사용한 클립은 v002(52초), v003(3분 20초), v005(37초)입니다. 원본에서 2–3분 길이 클립은 v003 하나뿐이라, 편집본 길이 약 2분을 목표로 세 클립을 썼습니다.

| ID | tag | source | 편집 길이 | 내용 |
| --- | --- | --- | --- | --- |
| c01 | mood | p005 | 5.0s | 야자수 인피니티 풀, `place` 베트남 푸꾸옥 |
| c02 | mood | p245 | 5.0s | 해 질 녘 바 뒷모습 |
| c03 | mood | p270 | 5.0s | 노을 앞에서 돌아본 인물 사진 |
| c04 | fun | p284 | 3.5s | 동행 뒷모습 + `(야시장 갈 체력 충전 중)` |
| c05 | mood | p291 | 4.5s | 칵테일 + "여기까지는 평화로웠다"(다음 컷 반전 복선) |
| c06 | fun | v002 0:00–0:25 | 20.4s | "대혼돈의 여행" → 길 건너기 → 미니 킹콩마트 |
| c07 | fun | v003 0:23–0:43 | 13.0s | "무서운데?" → "언니들이랑 같이 건너" |
| c08 | mood | v003 1:17–1:25 | 8.0s | 푸꾸옥 야시장 아치 간판 |
| c09 | fun | v003 1:38–1:47 | 8.5s | 리얼 진주 감별 |
| c10 | mood | v003 1:47–1:55 | 8.0s | 야시장 불빛 골목 |
| c11 | fun | v003 2:03–2:10 | 7.0s | 바람에 머리카락이 얼굴을 덮음 |
| c12 | fun | v003 2:34–2:56 | 14.9s | 보라색 크록스 → "그거 크록스 아니야?" (메인 웃음) |
| c13 | fun | v005 0:00–0:32 | 13.3s | "지금 마사지고 나발이고 호텔을 가고 싶어" (엔딩) |

- 합계 약 116초. 시간 기준 재미 69% · 감성 31%, 후보 수 기준 재미 7 · 감성 6
- 자막 비율: 예능 17 · 감성 6 · 대사 8 (예능 74%, 목표 범위 70–90% 안)
- 미리보기 영상: c06·c07·c08·c11·c12·c13

## 기대 화면 확인

- v1에서 c06(당시 ID) "현지인 따라가기 전략"과 c11(당시 ID) "오늘의 결론: 호텔"이 얼굴을 가려 위치를 옮김(v2). v3에서 감성 컷 2개를 추가하고 ID를 촬영 순서로 다시 매김

## 제한과 확인할 점

- 대사 자막 8개는 Whisper 전사 기반입니다. 사람이 듣고 확인하지 않았습니다(NOT_RUN). 특히 c06 "대혼돈의 여행", c12 "14,000원 한국 돈이", c13 문장
- 반복 문장(v003 01:54–02:04·03:05–03:17, v004 00:39 이후, v005 "날씨장")은 환각 의심으로 쓰지 않았습니다. 자동 `의심` 표시는 known_phrase만 잡았습니다
- 사진 contact sheet가 `index.md` 번호와 약 28장 어긋나고, 30장이 안 되는 마지막 묶음이 빠집니다. 이번에는 thumbnail을 직접 보고 ID를 확정했습니다. `photo_sheet` 수정은 다음 기능 후보입니다
- 세로 사진은 `objectFit: contain`이라 16:9 화면 좌우에 검은 여백이 생깁니다. 흐린 배경 채우기는 렌더러 개선 후보입니다
- 등록된 음원이 0개라 BGM·효과음은 계획만 적었고 미리보기는 현장음만 들어갑니다
- `./init.sh` doctor가 `asr: NOT_INSTALLED`를 보고하지만 분석의 전사는 `done`이었습니다. doctor의 ASR 판정 기준 확인이 필요합니다
- 감성 비중(31%)은 목표 40%보다 낮습니다. 야간 클립 대부분이 대화 중심이라 감성 구간 후보가 적었습니다

## 다음 허용 행동

사용자가 `review/v3/index.html`을 보고 채팅으로 채택·제외·자막 수정·순서를 답하면 `selection.json`으로 옮기고 `review.py select`로 기록합니다. 조립·렌더·음원 탐색은 사용자가 따로 요청할 때만 합니다.

## 2차 후보 (review v7) · 남자 출연자 제외

사용자 요청(2026-10-19): 같이 출연한 남자 출연자의 분량은 모두 제외 또는 음소거하고, 여자 출연자의 개인 브이로그로 정리합니다.

- 방법: 구간 음소거 기능이 없습니다. 조립 단계의 후보 전체 `original_gain_db`만 있고, 리뷰 미리보기에는 적용되지 않습니다. 그래서 남자 목소리나 모습이 있는 구간은 **컷에서 빼는 방식**으로 처리했습니다.
- 목소리 판정: 전사 문장별 F0와 여성 음역(160–450 Hz) 주기성을 쟀습니다(scratchpad 스크립트, 순수 Python 자기상관). 남성 판정과 불확실 판정은 모두 제외했습니다. 휴리스틱이며 사람 청취(NOT_RUN)를 대신하지 않습니다.
  - v002 전체(0–52초)와 v001은 남성 음역으로 판정해 제외했습니다("대혼돈의 여행" 포함).
  - v003 차도 구간(0–74초)은 소음 때문에 판정 불가라 제외했습니다(길 건너기 후보 포함).
- 화면 판정: 후보 구간을 1초 간격으로 확인한 뒤 남은 컷을 0.5초 간격으로 다시 확인했습니다. 남자 출연자가 보이는 v003 88–103초, 127–131초, 155–160초는 제외했습니다(크록스를 들어 보이는 순간 포함).
- 사진: 남자 출연자 사진(바 뒷모습, 수영장, 그네, 셀카)과 그일 가능성이 있는 원경 수영자 사진(p005)을 뺐습니다. 여자 출연자 사진 p053·p161·p185를 넣었습니다.
- 클립은 v003·v005 2개입니다. v004(반복 환각 전사, 46초 이후 남자 등장)와 v006(화자 혼재)은 넣지 않았습니다.

| ID | tag | source | 길이 | 내용 |
| --- | --- | --- | --- | --- |
| c01 | mood | p053 | 5.0s | 수영장에서 웃는 얼굴, `place` 베트남 푸꾸옥 |
| c02 | fun | p161 | 3.5s | 야자수 그네 발견 |
| c03 | fun | p185 | 3.5s | (인생샷 나올 때까지 무한 반복) |
| c04 | mood | p245 | 5.0s | 해 질 녘 바 뒷모습 |
| c05 | mood | p270 | 5.0s | 노을 앞에서 돌아본 순간 |
| c06 | mood | p291 | 4.5s | 칵테일 + "여기까지는 평화로웠다" |
| c07 | mood | v003 1:17–1:24 | 5.6s | 야시장 아치, 남성 음역 대사 1초를 잘라 2컷 |
| c08 | fun | v003 1:44–1:47 | 3.2s | "여기도 진짜 리얼 진주를 파는 거야" |
| c09 | mood | v003 1:47.5–1:50.9 | 3.4s | 불빛 골목 |
| c10 | fun | v003 2:04–2:07 | 3.0s | 바람에 머리카락 |
| c11 | fun | v003 2:41–2:55 | 7.2s | "14,000원" → "그거 크록스 아니야?" → "크록스라고 써 있긴 함" |
| c12 | fun | v005 0:06–0:37 | 17.8s | "사야 되는 건 보이지 않아?" → "마사지고 나발이고 호텔" |

- 합계 약 67초, 시간 기준 재미 58% · 감성 42%
- 자막 비율: 예능 13 · 감성 6 · 대사 5 (예능 68%, 목표 범위보다 2%p 낮음. 억지로 늘리지 않음)
- 리뷰 v4는 Write가 거부된 상태에서 build가 실행돼 v3과 같은 후보로 만들어졌습니다. 지우지 않고 보존합니다. v5–v6은 중간 버전이고, 현재 기준은 v7입니다.

### 남은 확인

- 사람 청취: 남은 컷에 남자 목소리(배경 대화 포함)가 섞였는지, 대사 자막 5개가 정확한지 확인해야 합니다(NOT_RUN).
- 길이: 남자 출연자 구간을 빼면서 2–3분 목표보다 짧아졌습니다. 늘리려면 (1) 사용자가 판정 불확실 구간(v003 길 건너기, v006 마무리 멘트)을 듣고 여자 목소리인지 확인하거나, (2) 구간 음소거 기능을 추가해 화면만 쓰는 방법이 있습니다.

## 선택 기록 (review v8)

사용자 답(2026-10-19): "c11 제외 나머지 채택. 남은 영상에서도 남자 출연자가 있다는 걸 알아채지 못하도록 목소리와 등장 장면을 모두 편집".

추가 편집(v8):
- 0.1초 프레임 음성 스캔(남성 음역 주기성 있음 + 여성 음역 없음): c07 두 번째 컷 01:21.7·01:23.4에서 검출 → 해당 컷 삭제. 나머지 컷은 검출 없음
- 0.2초 화면 확인: c07 01:17.0–01:17.2 오른쪽 끝 크림색 옷자락 → 시작을 01:17.6으로. c08 01:44.5·01:45.2–01:45.6 가장자리에 남자 출연자의 머리·옷·손이 보이고 1.3배 줌으로도 남음 → 제외
- 동행 암시 제거: c06 칵테일 두 잔(p291) → 한 잔과 짐벌(p298). c12 "그다지 우리가 사야 되는 건 보이지 않아?"(동행에게 묻는 말) 컷 삭제
- c12 끝부분 화면 가장자리의 인물 두 명은 낯선 행인으로 확인

선택: 채택 c01–c07·c09·c10·c12(10개), 제외 c08(지시에 따른 제외, note 기록)·c11(사용자 제외). 순서는 촬영 순서. state `selected/pending`.

- 채택본 길이 약 45초(사진 26.5초 + 영상 18.5초). 재미 c02·c03·c10·c12, 감성 c01·c04–c07·c09
- 남자 목소리 판정은 휴리스틱입니다. 사람 청취는 NOT_RUN입니다.
- 조립·렌더·음원은 요청 전까지 NOT_RUN입니다.

## 조립과 렌더

사용자 요청(2026-10-19): c11을 제외한 후보로 조립하고, 문제가 없으면 렌더. `production_render` 켜는 데 동의.

| 단계 | 결과 | 근거 |
| --- | --- | --- |
| 조립 | PASS | `assemble-report.md`: 45.0초, 클립 11, 후보 10. 확인할 점은 음원 없는 효과음 3개(c03·c10·c12) |
| `render_prod.py --check` | PASS | 예능 60%(목표 범위 밖) |
| 렌더 1차 | FAIL | QA `true_peak`: -0.36 dBTP. 믹스 -32.3 LUFS·-9.4 dBTP를 -14 LUFS로 올리는 과정에서 loudnorm이 동적 모드로 바뀌고 AAC overshoot가 더해짐. `render/v1/final.failed-20261019-095018.mp4`로 보존 |
| 렌더 재개 | PASS | `render/v1/final.mp4`, `verify.json`: 1350프레임, 45.0초, -12.89 LUFS, -1.68 dBTP, 체크 8개 모두 true. 끝난 구간 재사용 |

- 코드 변경: `scripts/render_prod.py` loudnorm 뒤에 `alimiter=limit=0.75`(-2.5 dBFS). 전체 테스트 112개 PASS(setup 설정 사본, skip 6)
- 최종 영상 1.5초 간격 확인: 남자 출연자 없음. 사람 시청·청취는 NOT_RUN
- 렌더 후 `production_render`를 다시 `false`로 돌림
- 제한: BGM과 효과음 음원이 없어 앞 26.5초(사진 6장)는 무음입니다. 세로 사진은 좌우가 검은 여백입니다. 예능 자막은 60%입니다.

## 2차 렌더: 음원·사진 오버레이·음소거 (render/v2)

사용자 요청(2026-10-19): `assets/audio`의 YouTube 허용 BGM·효과음을 어울리게 적용(무료 음원 검색·다운로드도 허락). 사진은 전체 화면이 아니라 관련 영상 한쪽에 띄우기. 남자 출연자 목소리는 자연스럽게 음소거. 다시 렌더.

- 음원: 사용자 파일만 사용했습니다(검색·다운로드는 하지 않음, 플래그도 false 유지). 등록한 음원은 bgm-vacation-uke, bgm-sunset-dream, bgm-snack-time, sfx-small-bell, sfx-pop, sfx-swoosh, sfx-beep-short, sfx-punchline-drum이고, 근거는 사용자 확인입니다. sfx-magic-chime은 -34 LUFS로 너무 작아 등록만 하고 쓰지 않았습니다. 곡 선택은 제목·장르 기준이며 청취는 NOT_RUN입니다.
- 새 기능: 후보 `plan.inserts`(사진 오버레이)와 `plan.mute`(원음 구간 음소거)를 추가했습니다. 변경 파일은 `scripts/production.py`(timeline `overlays` 검증), `scripts/sound.py`(`mute_envelope`·`map_mutes`), `scripts/assemble.py`, `scripts/review.py`, `renderer/src/production/PhotoInsert.tsx`(폴라로이드 카드), `ProductionTimeline.tsx`, `CandidatePreview.tsx`입니다. 원음을 통째로 끈 후보는 BGM ducking에서 뺍니다.
- 테스트: `tests/test_inserts.py` 6개를 추가했습니다. 전체 118개 PASS(setup 설정 사본, skip 6), typecheck·lint PASS
- 바탕 영상: 사진과 같은 장소의 가로 아이폰 클립 v011·v010(낮 수영장), v016·v018·v022·v030(노을)을 썼습니다. 0.5초 간격으로 확인했고 여자 출연자와 풍경만 나옵니다. 원음은 화자 확인이 어려워 끄고 BGM으로 채웠습니다. 요청 초기의 "클립 2–3개"보다 많아졌습니다.
- 음소거: 저에너지 0.1초 스캔에서 남성 음역이 나온 v003 01:18.7–01:19.7과 v005 00:22.3–00:23.1을 4프레임 페이드로 음소거했습니다.
- 리뷰 v9–v10, 선택(10개 채택, 순서 지정), 조립 56.9초(확인할 점 없음)
- 렌더 `render/v2/final.mp4`: 1707프레임, -14.21 LUFS, -1.27 dBTP, 체크 8개 PASS. 2초 간격 화면 확인에서 남자 출연자 없음. 사람 시청·청취는 NOT_RUN
- 렌더 후 `production_render`를 false로 돌림
- 재미·감성은 시간 기준 약 45 · 55, 예능 자막 62%

## 최종 렌더 (render/v3)

사용자 요청(2026-10-19): 노을 곡 Sunset Dream을 빼고 무료로 쓸 수 있는 곡을 찾아 적용, 클립 수와 나머지 분위기는 유지, 최종 렌더까지 진행.

- 다운로드 1건: Serene View - Arulo(Mixkit item 443, https://assets.mixkit.co/music/443/443.mp3, 3,647,991 bytes, sha256 556ae7a1…). 저장 위치 `assets/audio/library/mixkit-443/`, 등록 `bgm-serene-view`(origin claude_search). 이용 조건은 Mixkit Free Music License(https://mixkit.co/license/#musicFree)이고 no-claim 보증은 아닙니다. 사용자는 곡 선택을 Claude에게 맡겼고, 받은 뒤 파일 정보를 보고했습니다.
- gain -9 dB(곡 자체가 -14.8 LUFS로 다른 BGM보다 약 5 dB 작음). 노을 후보 c03–c06에 적용
- 리뷰 v11 → 선택(변경 없음) → 조립 56.9초(확인할 점 없음) → `--check` PASS
- `render/v3/final.mp4`: 1707프레임, 56.9초, -14.16 LUFS, -2.1 dBTP, 체크 8개 PASS, 200.9초 소요. 크레딧 첫 줄 "Music: Serene View - Arulo (Mixkit)"
- 렌더 후 `production_render`·`audio_search`·`audio_downloads`를 모두 false로 돌림
- 사람 시청·청취와 플랫폼 claim 확인은 NOT_RUN

## 피드백 반영 렌더 (render/v4, 2026-10-20)

사용자 피드백(2026-10-20): 마지막 대사 자막이 말보다 한참 먼저 나옴, 자막·효과음 variation 부족(특히 상단 노란 박스), 재미 연출 아쉬움(바람에 머리카락 장면), BGM은 추천+저장 곡을 비교해 고르고 싶음, 감성 자막의 미감 강화, "찰칵찰칵" 장면은 사진이 여러 장 쌓이게. 남자 출연자 편집은 자연스러움.

| 피드백 | 원인·조치 | 결과 |
| --- | --- | --- |
| 대사 자막 타이밍 | 거리 소음 영상에서 Whisper 시각이 약 2초 어긋남(같은 말이 창에 따라 25.98·27.0·27.5초). 단어 단위 전사 + 목소리 구간(음높이 주기성)으로 자막을 실제 목소리에 맞춤 | 호텔 대사 3.7초 → 목소리 구간 5.8–8.3초(편집 기준). 컷을 넘는 말도 한 자막 |
| variation | 자막 preset 14 → 33종(상단 박스 9종), 같은 preset 반복 경고 | 상단 박스: box-sky·sticker·ribbon·stamp 등으로 장면별 교체 |
| 재미 연출 | 효과(punch_zoom·shake·flash·speedlines)와 예능 화법 가이드 | 머리카락 장면: "푸꾸옥 바람 특보 발령" → 휘이잉+speedlines → "앞이 안 보여요"+punch_zoom → "(바람: 일부러 그런 거 아님)" |
| 감성 미감 | editorial·letter-fade·film-line·place-editorial preset, 영문 부제(`sub`), 폰트 2종 추가(Nanum Pen Script, Cormorant Garamond) | 오프닝 PHU QUOC, golden hour, before the night 등 |
| 사진 쌓기 | `inserts[].photos` 사진 쌓기와 셔터음 | 그네 사진 8장(p165–p193, 여자 출연자만)이 0.28초 간격으로 쌓임 |
| 음악 비교 | `bgm_options` 비교 미리보기(review v14) | 사용자 선택: 낮 Owies Ukulele, 엔딩 Clumsy Daddy |

- 다운로드(사용자 승인): Mixkit 효과음 15개(약 5.2MB), Mixkit BGM 3곡(Owies Ukulele·Summer Fun·Clumsy Daddy, 약 12.5MB), OFL 폰트 2종(약 5.1MB, Gowun Dodum은 예상보다 커서 받지 않음). 이후 audio_search·audio_downloads·production_render는 false
- 리뷰: v12는 c03 미리보기 delayRender 멈춤으로 실패해 보존. 리뷰 렌더러에 재시도를 넣고 v13·v14 생성(v13은 Whisper 시각만 사용, v14는 목소리 구간 사용). v15는 렌더용(미리보기 생략)
- 렌더 `render/v4/final.mp4`: 1707프레임, 56.9초, -14.22 LUFS, -1.66 dBTP, QA 8개 PASS, 205초
- 확인할 점: 예능 자막 65%(목표 80% 범위 밖, 억지로 늘리지 않음). Owies Ukulele는 원곡이 작아(-19 LUFS) BGM gain 상한 -6 dB에서 이전 곡보다 약 3 LU 작음. 사람 시청은 사용자 승인 2026-10-20("lgtm")
