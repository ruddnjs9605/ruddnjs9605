# 생생정보 → 네이버 블로그 초안 MVP

KBS 2TV **생생정보**의 공개 방송정보에서 식당 관련 사실과 출처를 추출하고 JSON·CSV·Markdown으로 저장하는 Python CLI입니다. API 키, DB, 생성형 AI, 네이버 로그인은 필요하지 않습니다. **자동 게시 기능은 없습니다.**

**현재 상태: 접속은 가능하지만 자동 수집·재이용 허락 미확인으로 상세 11412는 미요청이며, 실제 파서 검증과 5개 게시일 처리는 미완료입니다.** 실제 식당 데이터를 수집했다고 주장하지 않습니다.

## 11412 실제 데이터 검증 요청 결과 — 2026-10-19 KST (최신)

**이번 성공 기준인 실제 상세 HTML의 정확 파싱은 달성하지 못했습니다.** 네트워크 접속은 가능하지만 자동 수집·블로그 재이용 허락을 확인하지 못했고, 요청의 “자동 수집 허락이 불명확하면 요청하지 말라” 조건에 따라 `https://iaudience.kbs.co.kr/broadcast/11412` 본문은 요청하지 않았습니다. 홈페이지 접근이나 사용자가 제공한 비교 기준을 실데이터 수집 성공으로 계산하지 않았습니다.

### 1. 실제 HTML 확보 및 정책 조사

정책 확인 목적으로 공개 홈페이지의 푸터와 실제로 연결된 `kbs-common.js`, `front-common.js`를 조사했습니다. robots는 HTTP 404(파일 없음), 홈페이지와 공통 스크립트는 HTTP 200이었습니다. 푸터에는 개인정보처리방침·회사소개·저작권 표시는 있으나 자동 수집·블로그 재이용을 허용하는 문서를 찾지 못했습니다. 개인정보처리방침은 콘텐츠 재이용 허락을 대신하지 않습니다. 이 관찰만으로 KBS 전체가 수집을 금지하거나 허용한다고 판단하지 않습니다. [정책 조사 기록](outputs/11412-policy-research-01/report.json)은 로컬 outputs에 있습니다.

허락 미확인으로 자동 상세 요청을 보류했고 로그인·인증 우회, 프록시 해제, TLS 검증 비활성화, 방송 사진/영상 다운로드는 하지 않았습니다. 공식 API 계약이나 명시적 허락 근거, 또는 적법하게 제공된 HTML이 필요합니다.

### 2~4. 실제 처리 건수 및 추출 결과

| 항목 | 이번 결과 |
| --- | --- |
| 대상 상세 HTML 확보 | 0건 (정책 탐색용 홈페이지 조회와 구분) |
| 실제 방송정보 페이지 처리 | 0건 |
| 실제 프로그램/코너/장소 추출 | 각각 0건 |
| 네 장소의 이름·주소·코너 대조 | 미실행 |
| 실제 HTML 파서 검증 | 미실행 |
| 이전 게시일 포함 총 5개 페이지 검증 | 미실행 — 첫 상세 페이지 미검증 |

정확히 추출한 실제 장소 정보는 없습니다. 사용자 제공의 숭례분식·금화횟집·강변상회·풀내음 캠핑장과 주소/코너는 [외부 비교 기준 manifest](docs/manual-html/11412.reference-manifest.json)에만 보관했습니다. 파서/데이터셋에는 하드코딩하지 않았으며 사용자 기준도 실제 HTML과 일치하는지 미검증입니다. 다른 프로그램·코너의 동명 장소가 있으면 비교가 모호할 수 있어 유일한 `match`가 없으면 실패하도록 했습니다.

실제 DOM을 보지 못했으므로 프로그램별 전용 어댑터, 페이지→프로그램→코너→장소 계층의 실사이트 검증, 명시 가격/영업시간 추출은 보류했습니다. 기존 범용 파서와 import 경로는 유지했습니다. 현재 결과 파일에는 미완료 사유와 0건을 기록하고 실제 초안은 만들지 않았습니다.

### 5. 원방송일과 스페셜 편성일

이번 상세 원문에서는 추출·대조하지 못했습니다. 기존 원방송일/재방송일 분리 기능은 유지하며, 홈페이지의 10월 19일 스페셜 편성을 모든 장소의 원방송일로 채우지 않았습니다. 코너 제목을 대표 메뉴로 바꾸지 않았습니다. 실제 코너별 원방송일, 편성일/시간, 가격·영업시간은 확인 필요입니다.

### 6. 블로그 제목 후보 기능

`src/tvblog/candidates.py`와 `candidates` 명령을 추가했습니다. 기존 import/collect/review 출력에도 `candidates.json`을 추가로 저장합니다. 후보는 근거·출처가 있는 추출값만 사용하며, 사람이 승인한 사실과 미검토 추출값을 구분합니다.

- 추천 제목, 대상 프로그램/코너, 원방송 기준 날짜·편성일/시간(있을 때만), 관련 장소, 공식 출처
- `confirmed_facts`(사람 승인), `unreviewed_extractions`(미승인), `unknown_information`(가격/영업시간 등 누락)
- `예상 검색 키워드` 표시, 검색량/인기도는 `확인 필요`; 검색량/API/AI 서비스 미사용
- `draft_generation_possible`: 프로그램명·장소명·주소·원방송 기준 방송일을 사람이 승인한 경우만 true; 합성 자료는 항상 false
- `publication_ready`는 항상 false; 사실 검토나 초안 가능 상태가 재이용 허락을 보증하지 않음

검토 전 제목 문자열은 **검토 대기 제안**입니다. 추천 제목을 확정 사실이나 검증 완료된 콘텐츠로 취급하지 않습니다. 기존 Markdown은 승인 필드만 사용하며 자동 게시하지 않습니다.

**실제 데이터에서 생성된 제목 후보는 0개입니다.** 사용자 비교 기준으로 그럴듯한 실제 제목을 만들어 결과를 채우지 않았습니다. 기능 회귀 테스트의 가상 장소 후보는 실제 후보와 구분하며 실제 결과 디렉터리에 넣지 않았습니다.

```bash
.venv/bin/tvblog candidates --records outputs/kbs-11412-01/records.json --out outputs/kbs-11412-topics-01
```

독립 명령은 `candidates.json`, `candidates.csv`, `report.json`을 저장합니다. 근거가 있는 장소가 없으면 `no_eligible_records`와 종료 코드 2이며 빈 후보 배열을 저장합니다.

### 7. 자동 테스트

작업 시작 시 기존 테스트는 62개보다 늘어난 **80개**였습니다. 이를 모두 유지하고 신규 6개를 추가해 **86개 통과**했습니다. 후보의 근거/승인 구분, 미확인 지표, 날짜 분리, 합성 격리, 중복·누락, CLI 및 장소명 선택 비교를 검증했습니다. [테스트 실행 기록](docs/results/11412-validation-2026-10-19/offline-tests.txt).

실제 HTML 회귀 테스트는 **실행하지 않았습니다**. 합성 테스트 수 증가로 실제 파싱이 완료됐다고 주장하지 않습니다.

### 8. 생성 파일 및 코드

실제 작업 상태: [report.json](docs/results/11412-validation-2026-10-19/report.json)

- `docs/results/11412-validation-2026-10-19/records.json`: 빈 배열
- `records.csv`: 헤더만 있음
- `candidates.json`: 빈 배열
- `drafts/`: 실제 초안 없음 (빈 디렉터리는 Git에 보존되지 않을 수 있음)
- `docs/manual-html/11412.reference-manifest.json`: **사용자 제공 비교 기준**, 데이터셋 아님
- `src/tvblog/candidates.py` 신규, `cli.py`/`export.py` 확장, `importing.py`의 선택 비교 개선
- `tests/test_candidates.py` 신규, 기존 `test_importing.py`에 선택 비교 테스트 추가

기존 `parser.py`, 검토·승인 로직, 의존성은 변경하지 않았습니다. PostgreSQL·Cloud Run·자동 게시도 추가하지 않았습니다.

### 9. 다음 단계 — 실제 HTML 1건을 먼저 확보

1. 자동 수집/재이용 허락의 공식 근거가 있으면 해당 문서/URL을 확인합니다. 그 전에는 상세 요청 보호 조건을 해제하지 않습니다.
2. 정상 접근했고 제공이 허용되는 상세 HTML을 수동 확보한 경우 `11412.html`로 제공하면 기존 import와 아래 비교 기준으로 검증을 시작할 수 있습니다. [저장·제공 절차](docs/manual-html/README.md)를 따릅니다. 수동 제공도 무조건적 재이용 허락을 뜻하지 않습니다.
3. 실제 DOM에 맞는 어댑터가 필요하면 그 HTML을 근거로 구현하고 네 장소 및 코너/주소를 대조합니다. 기준과 다르면 불일치를 그대로 보고합니다.
4. 첫 페이지 파싱을 검증한 뒤에만, 허용되는 경로로 이전 게시일을 찾아 5개 게시일로 확대합니다.

```bash
cd /workspace/ruddnjs9605
mkdir -p inputs/kbs-11412
cp docs/manual-html/11412.reference-manifest.json inputs/kbs-11412/manifest.json
# 제공이 허용된 실제 HTML을 inputs/kbs-11412/11412.html로 저장한 후 실행합니다.
.venv/bin/tvblog import-html --manifest inputs/kbs-11412/manifest.json --out outputs/kbs-11412-01
.venv/bin/tvblog review-template --records outputs/kbs-11412-01/records.json --out outputs/kbs-11412-review.json
```

manifest의 `match`는 실제 추출 결과 중 장소명을 골라 비교할 뿐, 장소를 생성하거나 순서를 강제하지 않습니다. 동일 장소가 여러 프로그램에 있으면 실제 문서를 확인한 뒤 프로그램/코너 조건을 추가할 수 있습니다. 실제 HTML이 아직 없으므로 위 명령을 실사이트 검증에 성공한 명령으로 표기하지 않습니다.

---

## 공개 홈페이지 데이터 접근 확인 — 2026-10-19 KST

정책 링크를 조사하는 제한된 홈페이지 요청에서 `https://iaudience.kbs.co.kr/`가 HTTP 200과 `메인 | KBS 시청자상담실` HTML을 반환했습니다. 응답에는 실제 **생생정보 스페셜** 방송정보 링크와 **10월 19일 2TV 07:30~08:40** 편성 텍스트가 포함돼 있었습니다. 링크는 `/broadcast/11412`였습니다. 따라서 기술적으로 실제 공개 방송정보 텍스트가 내려오는 것은 확인했습니다. 이 편성 텍스트를 원방송일로 간주하거나 연도를 임의로 채우지 않았습니다.

이는 홈페이지 공개 텍스트 접근 확인이며 상세 방송정보 원문의 파서 검증 완료가 아닙니다. 상세 링크는 아직 요청하지 않았고 식당/장소 추출은 0건입니다. 재이용 조건이 미확인이라 자동 대량 수집으로 확대하지 않았습니다. 실제 관찰 요약은 로컬 `outputs/data-availability-check-01/report.json`에 기록했습니다. 전체 홈페이지/원문/사진은 저장하지 않았습니다.

## 설정 재게시 후 재확인 — 최신 상태 (2026-10-19 KST)

이번 설정 게시 후 **KBS 6개 모두 CONNECT·TLS에 성공**했습니다. `iaudience.kbs.co.kr`도 HTTP 200으로 바뀌었습니다. `apis` 루트의 HTTP 404는 연결 성공 후 경로 응답이며 프록시 차단이 아닙니다. 일반 `example.com`은 계속 CONNECT 403, GitHub는 HTTP 200입니다. [실제 진단 결과](outputs/after-publish-check-02/report.json)는 로컬 outputs에 저장했습니다(버전 관리 제외).

`iaudience` robots 요청은 **HTTP 404(파일 없음)**였습니다. 현재 클라이언트의 `allows_path` 표시는 이 경우를 포함하므로 사이트가 명시적으로 수집을 허가했다는 뜻이 아닙니다. 후보 4개 경로는 robots 지시로 금지된 것으로 확인되지 않았지만, 이용약관·데이터 재이용 허락은 미확인입니다. 공개 홈 HTML은 정책 링크 확인 목적으로 1회 조회했고 관련 링크를 찾지 못했습니다. 방송정보 상세 HTML은 요청하지 않았습니다. [정책 접근 기록](outputs/after-publish-check-02/iaudience-policy.json), [홈 정책 탐색 기록](outputs/after-publish-check-02/policy-navigation.json).

따라서 ‘KBS 전체가 공식적으로 크롤링 금지’라고 확정할 근거도, 수집·블로그 재이용이 허용됐다고 확정할 근거도 아직 없습니다. 이전 설명의 iaudience 접속 실패는 현재 상태로 대체해야 합니다. 불확실한 상태에서 방송정보 자동 수집을 진행하지 않았으며, 실제 방송정보 원문 확보·파싱은 여전히 0건입니다. 정책 확인 전 수집 보호 조건은 유지했고 코드 변경이나 반복 차단 요청은 하지 않았습니다.

아래 A~D와 네트워크 차단 기록은 이전 실행 이력입니다.

## 실제 공식 HTML 1건 검증 시도 — 2026-10-19 KST (최신 결과)

**핵심 목표는 미완료입니다. 실제 KBS HTML을 확보하지 못해 1건 정확 파싱 검증을 시작하지 못했습니다.** 기존 코드·README를 먼저 분석하고 기존 62개 테스트 통과를 확인했습니다. 아래 결과는 이후 작업 기록보다 최신입니다. 새 프로젝트나 실제 데이터처럼 보이는 HTML을 만들지 않았고, 실제 DOM을 보지 않은 상태에서 `parser.py`를 추측 수정하지 않았습니다.

### A. 네트워크

**CONNECT 403은 해결되지 않았습니다.** 일반 2개와 대상 KBS 6개를 **한 번씩** HEAD 요청으로 비교했습니다. [이번 실제 실행 보고서](docs/results/one-page-validation-2026-10-19/network/report.json)에 요청 시각과 결과가 있습니다. 진단 종료 코드는 2입니다.

| 호스트 | 로컬 DNS | 프록시 CONNECT | TLS | 터널 이후 HTTP |
| --- | --- | --- | --- | --- |
| `example.com` | 실패 | 403 | 도달 안 함 | 도달 안 함 |
| `github.com` | 실패 | 200 | 인증서 검증 성공 | 200 |
| `program.kbs.co.kr` | 실패 | 403 | 도달 안 함 | 도달 안 함 |
| `www.kbs.co.kr` | 실패 | 403 | 도달 안 함 | 도달 안 함 |
| `schedule.kbs.co.kr` | 실패 | 403 | 도달 안 함 | 도달 안 함 |
| `pbbs.kbs.co.kr` | 실패 | 403 | 도달 안 함 | 도달 안 함 |
| `apis.kbs.co.kr` | 실패 | 403 | 도달 안 함 | 도달 안 함 |
| `iaudience.kbs.co.kr` | 실패 | 403 | 도달 안 함 | 도달 안 함 |

프록시 변수는 존재 여부만 확인했고 값·주소·인증정보는 출력하지 않았습니다. GitHub는 로컬 DNS 실패 상태에서도 프록시를 통해 성공하므로, 로컬 DNS 실패를 KBS CONNECT 거부의 원인으로 단정하지 않습니다. KBS 원본 서버가 직접 403을 반환했다고도 단정하지 않습니다. 프록시 해제·직접 연결·인증서 검증 해제·네트워크 회피는 하지 않았습니다.

환경 설정 관찰은 다음과 같습니다. [설정 관찰 기록](docs/results/one-page-validation-2026-10-19/environment.json)을 보관합니다.

- **편집 설정 초안에서 확인됨:** 제한 네트워크, 기존 패키지 관리자 프리셋, 대상 KBS 도메인 6개 전부가 사용자 지정 허용 목록에 존재합니다. 누락이 없어 이번 작업에서는 네트워크 초안을 수정하지 않았습니다.
- **실행에서 확인됨:** 프록시가 사용되며 GitHub는 연결되고 KBS 6개는 CONNECT 단계에서 거부됩니다. 이것이 실제 동작으로 확인한 접근 범위입니다.
- **확인 불가:** 현재 인스턴스에 적용된 설정 버전·전체 실행 허용 목록·조직/플랫폼 egress 정책·설정 초안과 실행 버전의 정확한 차이. 제공된 도구는 편집 설정 조회이고 실행 인스턴스 상태 조회 도구는 없습니다.
- **새 실행 환경 필요 여부:** 확인 불가입니다. 설정 저장/게시/복원/새 작업 생성은 각각 다른 동작입니다. 새 환경이 반드시 필요하거나 재시작만으로 해결된다고 주장하지 않습니다.

이미 같은 CONNECT 403을 확인했으므로 추가 robots/상세 본문 GET이나 동일 요청 반복, 최근 5회 수집을 진행하지 않았습니다. 별도 상태 변화가 있기 전까지 재시도하지 않습니다.

### B. 실제 데이터

| 항목 | 이번 결과 |
| --- | --- |
| 실제 KBS HTML 확보 | **0건** |
| 실제 방송정보 수집 | **0건** |
| 실제 식당·장소 추출 | **0건** |
| 실제 HTML 파서 검증 | **미실행** |
| 실제 1건 검증 후 최근 5회 확대 | **미실행 — 선행 1건 미확보** |

사용자가 지정한 `/broadcast/`, `/broadcast/11344`, `/broadcast/11279`, `/broadcast/11234`는 이번에도 후보일 뿐입니다. CONNECT 차단으로 본문·robots·약관·재이용 조건을 확인하지 못했습니다. 따라서 목록 DOM, 상세 DOM, 방송일/게시일 위치, 프로그램/코너 위치, 상호/주소/메뉴 구조, JavaScript 동적 렌더링 필요 여부는 모두 **미검증**입니다. [후보별 미확보 기록](docs/results/one-page-validation-2026-10-19/source-status.json)을 남겼습니다. 허용된 실제 HTML이 들어오기 전 전용 어댑터나 실제 fixture를 만들어 검증했다고 보고하지 않습니다.

### C. 코드

이번에 변경/추가한 파일은 다음과 같습니다. 기존 소스·기능을 유지하고 오프라인 입력 준비만 보강했습니다.

- `src/tvblog/diagnostics.py`: 대상 KBS 6개를 포함하는 진단 호스트 집합 추가. 기존 기본 진단 4개는 유지합니다.
- `src/tvblog/cli.py`: `diagnose --all-kbs` 추가, 기존 `import-html` 처리를 새 helper로 연결. 기존 모든 명령/인자는 유지합니다.
- `src/tvblog/importing.py` 신규: manifest 구조 검증, 원문 URL 매핑, 경로/심볼릭 링크 경계 확인, 파일 크기 제한, 명시 인코딩, SHA-256, 출처 취득 기록, DOM 구조 요약, 선택적 기대값 비교.
- `tests/test_importing.py` 신규 및 `tests/test_diagnostics.py` 추가 테스트: 외부 요청 없는 import, 잘못된 입력·인코딩·기대값 실패, DOM 불명확 상태, 승인 미승격 및 전체 호스트 전달 검증.
- `docs/manual-html/README.md`, `manifest.example.json` 신규: 실제 HTML 한 파일을 저장·제공·검증하는 절차. **실제 HTML은 포함하지 않습니다.**
- `README.md`와 `docs/results/one-page-validation-2026-10-19/`: 이번 보고서·실제 네트워크 결과·테스트 결과.

**기존 62개 테스트를 유지하고 신규 18개를 추가해 총 80개 통과했습니다.** [현재 테스트 결과](docs/results/one-page-validation-2026-10-19/offline-tests.txt). 신규 테스트는 기존 합성 fixture/실패 입력을 이용한 회귀 테스트이며 실제 방송자료 검증은 아닙니다.

기존 JSON·CSV·Markdown 출력과 `review-template`/`review`를 유지합니다. parser와 사용자 승인 로직 자체는 변경하지 않았습니다. 자동 게시, PostgreSQL, Cloud Run 배포도 추가하지 않았습니다.

import 결과의 `inspection`은 컨테이너/제목/표/스크립트/iframe 등의 **구조 통계**입니다. 전문·스크립트 코드·외부 에셋은 요약에 복제하지 않으며, 외부 링크를 요청하거나 JavaScript를 실행하지 않습니다. 스크립트가 있다는 사실만으로 동적 렌더링 필수라고 추정하지 않습니다.

`expected_records`를 manifest에 넣으면 원문을 보고 사람이 지정한 기대값과 실제 추출 결과를 비교할 수 있습니다. 불일치하면 `expectation_failed` 및 종료 코드 2로 실패하고 진단 결과는 보존합니다. 기대값 일치도 원문 진위·정책 허락·독립 검증을 보장하지 않으며 필드를 `human_verified`로 바꾸지 않습니다. 실제 원문과 대조한 사람의 기존 `review` 승인이 따로 필요합니다. 본문을 못 읽거나 추출 0건이면 `unparsed`로 보고합니다.

### D. 다음 사용자 작업

#### Codex 설정

도구로 확인할 수 있는 제품 동작은 **환경 설정에서 검토·저장한 뒤 환경 게시(Publish)**하는 절차입니다. 현재 화면을 볼 수 없어 환경 설정 진입 버튼 위치나 네트워크 하위 섹션의 정확한 표시 이름은 확인 불가능합니다. 존재를 확인하지 못한 메뉴를 만들어 안내하지 않습니다.

1. 사용 중인 Codex 클라우드 환경의 **환경 설정**을 엽니다.
2. 네트워크/인터넷 접근의 사용자 지정 허용 목록에 위 6개 도메인이 있는지 확인합니다. 현재 초안에는 이미 모두 있으므로 같은 도메인을 중복 추가하거나 기존 항목을 지울 필요가 없습니다.
3. 아직 적용하지 않은 초안이라면 **저장 → 게시(Publish)**를 진행합니다. 초안 저장만으로 실행 적용이 완료된 것으로 보지 않습니다.
4. 이미 저장/게시한 상태라면 같은 작업을 반복하기보다 플랫폼 관리자/지원에 이번 보고서를 전달하고 **현재 실행 인스턴스의 적용 egress 정책/설정 버전과 CONNECT 거부 이유**를 확인해야 합니다. 새 작업 환경이 필요하다는 안내를 받았다면 새 환경에서 아래 진단으로 비교합니다. 지금 도구로 필수 재시작/새 환경 여부를 확정할 수는 없습니다.

설정 상태가 실제로 달라진 후에만 다시 진단하세요. 아래 명령은 경로가 이미 있으면 새 출력 경로로 바꿔야 합니다.

```bash
cd /workspace/ruddnjs9605
.venv/bin/tvblog diagnose --all-kbs --out outputs/network-after-settings-01
```

#### 실제 HTML 1건 제공

네트워크 해결을 기다리는 동안에도 **정상 접근했고 이용 조건상 제공 가능한 공식 HTML 1개**가 있으면 오프라인 검증을 시작할 수 있습니다. [파일 저장·제공 상세 절차와 기대값 작성법](docs/manual-html/README.md)을 따르세요.

1. 공개 공식 상세 페이지에서 정책상 허용되는 범위를 확인한 뒤, 본문이 표시된 상태에서 브라우저 **저장 → HTML만**으로 `broadcast.html`을 저장합니다.
2. 저장 파일에 표시된 본문이 빠져 있다면 허용되는 경우에만 개발자도구에서 현재 표시된 DOM의 outerHTML을 수동 복사해 UTF-8로 저장합니다. 자동 수집이나 차단 우회와 구분합니다.
3. 이 채팅에 HTML 파일을 첨부하고 브라우저 주소창의 최종 원문 URL을 함께 알려주세요. 가능하면 저장 시각·방법·직접 확인한 이용 조건도 알려주세요. 파일과 manifest를 함께 제공해도 됩니다. PDF/화면 캡처/URL만으로는 실제 DOM을 검증할 수 없습니다.
4. HTML과 manifest를 `/workspace/ruddnjs9605/inputs/kbs-one/`에 함께 놓습니다. manifest는 [예시](docs/manual-html/manifest.example.json)를 복사해 실제 파일/원문 URL/취득 기록으로 수정하세요. 예시 페이지의 내용이나 허락을 검증했다는 뜻이 아닙니다.

```bash
cd /workspace/ruddnjs9605
.venv/bin/tvblog import-html --manifest inputs/kbs-one/manifest.json --out outputs/kbs-one-01
.venv/bin/tvblog review-template --records outputs/kbs-one-01/records.json --out outputs/kbs-one-review.json
```

원문 대조 기대값을 manifest에 추가하면 같은 import 명령을 새 출력 폴더로 실행해 바로 비교할 수 있습니다. `report.json`의 구조 요약과 파싱 경고로 필요한 어댑터 변경을 판단할 수 있습니다. **별도 개발 없이 입력/분석/기대값 테스트를 시작할 수 있지만, 아직 보지 못한 실제 DOM의 파싱 성공을 보장하지는 않습니다.** 실제 1건을 검증한 뒤에만 정책상 허용된 범위에서 5회로 확대합니다.

---

## 추가 개발 및 재진단 — 2026-10-19 KST

### 실제 확인한 사실

일반 HTTPS와 KBS 연결을 HEAD 요청으로 비교했습니다. 프록시를 해제하거나 우회하지 않았으며 TLS 인증서 검증도 유지했습니다. [네트워크 실행 결과](docs/results/followup-2026-10-19/network-cli/report.json)는 프록시 변수의 **설정 여부만** 저장하고 값·주소·인증정보·curl 원문 로그는 저장하지 않습니다.

| 목적지 | 컨테이너 로컬 DNS | CONNECT 프록시 | TLS | 프록시 터널 이후 HTTP |
| --- | --- | --- | --- | --- |
| `example.com` | 실패 | 403 거부 | 도달 안 함 | 도달 안 함 |
| `github.com` | 실패 | 200 성공 | 인증서 검증 성공 | 200 |
| `program.kbs.co.kr` | 실패 | 403 거부 | 도달 안 함 | 도달 안 함 |
| `iaudience.kbs.co.kr` | 실패 | 403 거부 | 도달 안 함 | 도달 안 함 |

`HTTP_PROXY`, `HTTPS_PROXY` 및 소문자 변형과 `NO_PROXY` 계열이 설정돼 있었습니다. 프록시 변수의 값이나 비밀정보는 출력하지 않았습니다. 로컬 DNS는 별도 관찰입니다. **로컬 DNS가 실패해도 프록시를 통해 GitHub에는 연결됐으므로, DNS 실패를 KBS CONNECT 403의 원인으로 단정할 수 없습니다.** 프록시의 목적지 이름 해석 방식과 내부 정책은 확인하지 못했습니다.

설정 도구에서 기존 KBS 호스트 5개가 저장된 제한 네트워크와 초기 조사 때보다 변경된 기준 버전을 관찰했습니다. 진단 시 `iaudience.kbs.co.kr`는 목록에 없었습니다. 그러나 이미 목록에 있던 `program.kbs.co.kr`도 여전히 차단되므로, 신규 도메인 누락만으로 전체 실패를 설명할 수 없습니다. 도구는 편집 설정 정보를 보여주며 실행 인스턴스에 적용된 버전은 제공하지 않습니다. **새 환경 생성 여부·현재 머신에 적용된 설정 버전은 확인 불가**입니다. [설정 관찰 기록](docs/results/followup-2026-10-19/environment-observation.json)을 남겼습니다.

### 신규 공식 후보 및 정책 확인 결과

다음 URL을 사용자가 제공한 공식 후보로 등록했습니다. URL을 등록했다는 사실은 내용·회차·유효성을 검증했다는 뜻이 아닙니다.

- <https://iaudience.kbs.co.kr/broadcast/>
- <https://iaudience.kbs.co.kr/broadcast/11344>
- <https://iaudience.kbs.co.kr/broadcast/11279>
- <https://iaudience.kbs.co.kr/broadcast/11234>

robots.txt 요청이 프록시에서 실패해 네 페이지 **본문은 요청하지 않았습니다**. 동일 호스트의 공통 정책 접근 실패는 한 번만 요청하고 네 후보에 각각 기록했습니다. [실제 정책 접근 보고서](docs/results/followup-2026-10-19/policy-probe/report.json)에서 `content_requested=false`, `terms_permission=unverified`, `api_contract=unverified`를 확인할 수 있습니다.

이용약관·콘텐츠 재이용 허락·문서화된 API를 확인하지 못했습니다. 자동 대량 수집을 실행하지 않았으며 신규 `iaudience`의 라이브 본문 요청은 코드에서도 `policy_review_required`로 차단합니다. robots가 허용하더라도 자동으로 이용 허락이 확인된 것으로 취급하지 않습니다. 현재 이 소스를 처리하는 경로는 **적법하게 확보한 HTML의 import**입니다. 라이브 수집을 활성화하는 플래그는 추가하지 않았습니다.

### 테스트 성공 항목

기존 31개 테스트를 유지하고 신규 31개를 추가해 **총 62개가 통과**했습니다. [이번 테스트 출력](docs/results/followup-2026-10-19/offline-tests.txt)을 보관합니다.

- 프록시 CONNECT 거부·TLS 실패·원본 HTTP 오류 단계 구분과 비밀정보 로그 방지
- 프로그램·게시일·방송일·코너·장소 유형·장소명·소개 음식·주소 추출
- 원방송일·재방송일 분리, 스페셜 일반 날짜의 잘못된 원방송일 대입 방지
- 코너별/장소별 원방송일 분리, 장소 간 메뉴·유형 누출 방지
- 게시일을 방송일로 사용하지 않기, 누락·충돌·불가능한 날짜 순서 처리
- 목록의 스페셜/재방송을 신규 원방송 날짜 선택에서 제외
- 신규 소스 정책 미확인 시 본문 요청 차단 및 기존 JSON 내보내기 호환
- `import-html`로 가상 식당·여행지 2건을 JSON·CSV·Markdown으로 처리

[추가 합성 실행 결과](docs/results/followup-2026-10-19/synthetic-special/records.json)의 식당·주소·메뉴·날짜·출처 경로는 모두 가상입니다. 실제 방송정보가 아닙니다.

### 미검증 항목

**실제 HTML은 제공되지 않았고 수집하지도 못했습니다. 실사이트 파서 검증은 실행하지 않았습니다.** 기존 `tests/fixtures/detail.html`과 새 `tests/fixtures/synthetic/` 모두 합성 자료입니다. `tests/fixtures/real/README.md`는 실제 HTML 미확보 상태를 설명하며 실제 사이트 테스트 통과를 뜻하지 않습니다.

실제 KBS DOM, 메타데이터의 위치/표기 방식, 네 페이지의 내용과 날짜, 공개 API 존재 여부, 자동 수집·블로그 재이용 허락, 현재 클라우드 인스턴스의 정책 적용 여부는 미검증입니다. Python 3.11/3.13의 CI 구성은 있으나 이번 실행은 3.12에서만 수행했습니다.

### 네트워크 차단 단계

현재 증거가 가리키는 실패는 **CONNECT 프록시 단계의 403**입니다. KBS로의 TLS 협상과 콘텐츠 HTTP 요청은 도달하지 못했습니다. KBS 서버가 반환한 콘텐츠 403이나 robots 금지로 단정하지 않으며, 이 결과를 파서/수집 코드 버그라고 단정하지 않습니다. 회사 PC의 로컬 망, 조직 정책, 프록시 내부 정책 중 무엇이 최종 원인인지는 현재 관찰만으로 확정할 수 없습니다.

새 진단 명령은 다음과 같습니다. curl이 없으면 `diagnostic_unavailable`로 보고하며 연결 성공으로 처리하지 않습니다. 진단은 네 목적지에 HEAD만 보내고 리디렉션은 따라가지 않습니다. 기존 프록시 설정을 유지하며 DNS 관찰은 최대 6초, curl 요청은 최대 12초로 제한합니다.

```bash
tvblog diagnose --out outputs/network-new-run
tvblog probe --out outputs/policy-new-run
```

### 추가로 필요한 사용자 작업

1. 환경 설정 초안에 **기존 사용자 지정 도메인과 프리셋을 보존하며 `iaudience.kbs.co.kr`를 추가**했고 시작 지침을 갱신했습니다. 설정에서 검토·저장한 다음 환경을 게시해야 활성화할 수 있습니다. 초안 저장은 실행 환경 적용이나 게시를 의미하지 않습니다.
2. 이미 설정을 적용했다면, 플랫폼 관리자/지원 담당자에게 `program.kbs.co.kr:443` CONNECT 403과 `github.com:443` 성공 비교를 전달하고 **실행 인스턴스에 적용된 egress 정책과 버전**을 확인해야 합니다. 게시/재시작만으로 해결된다고 보장할 수 없습니다.
3. 네트워크가 복구되더라도 robots·이용약관·재이용 허락과 API 제공 여부를 먼저 확인하세요. 대량 수집은 허용 근거가 확인된 후에 진행해야 합니다. 현재 신규 소스의 라이브 본문 수집 보호 조건은 별도 검토 없이 해제하지 않습니다.
4. 접근 가능한 곳에서 정책상 허용된 공식 HTML을 직접 확보했다면 `import-html`을 사용할 수 있습니다. 파일은 UTF-8로 저장하고, 실제 원문 URL·확보 시점·허용 근거를 함께 보관하세요. 브라우저 저장 파일과 manifest의 진위/허락은 도구가 자동 확인하지 않습니다.

```json
{
  "sources": [
    {"file": "broadcast.html", "source_url": "https://iaudience.kbs.co.kr/broadcast/11344"}
  ]
}
```

위 예시는 원문 URL 매핑 형식일 뿐 해당 페이지에 어떤 방송이 담겼는지 확인했다는 뜻이 아닙니다.

```bash
tvblog import-html --manifest /path/to/permitted/manifest.json --out outputs/import-new-run
# 네트워크 없는 합성 실행: 실제 방송 자료가 아닙니다.
tvblog import-html --manifest tests/fixtures/synthetic/manifest.json --fixture --out outputs/special-demo-new-run
```

### 최근 실제 5회분의 수집 성공 여부

**미완료입니다. 실제 확인한 방송 0회, 실제 수집 장소 0건입니다.** 이번 작업에서는 정책 접근 단계에서 중단했고 허락이 미확인인 신규 소스에 5회 일괄 수집을 보내지 않았습니다. 종전 5회 수집 시도의 실패 보고서는 아래 초기 실행 기록에 보존했습니다. 합성 자료 2건과 오프라인 테스트 성공을 실제 5회 수집 성공으로 계산하지 않습니다.

## 확장 데이터 구조와 날짜 의미

기존 모듈 구조와 명령을 유지하면서 JSON 레코드에 `schema_version=2`를 추가했습니다. 기존 5개 필드도 유지합니다.

| facts 필드 | 의미 |
| --- | --- |
| `program_name` | 명시 프로그램명 또는 제목에 명시된 알려진 프로그램명; 없으면 확인 필요 |
| `broadcast_date` | 일반 방송의 실제 방송일 / 스페셜에서는 명시된 원방송일 기준 호환 필드 |
| `original_broadcast_date` | 원방송일·원본방송일·최초방송일·본방송일로 명시된 날짜 |
| `rebroadcast_date` | 재방송일로 명시된 날짜 |
| `posted_date` | 게시일·등록일·작성일로 명시된 날짜; 방송일로 재사용하지 않음 |
| `is_rebroadcast` | 명시된 예/아니오, 또는 명시적인 재방송일 근거의 예; 나머지는 확인 필요 |
| `corner_name` | 명시된 코너/코너명 |
| `place_type` | 명시 유형 또는 식당명·여행지명·숙소명 등의 분명한 라벨; 일반 상호로 유형 추정 안 함 |
| `name`, `address` | 명시 장소 이름·주소 |
| `introduced_menu` | 소개된 음식/메뉴; 일반 메뉴도 저장하지만 대표 여부는 추정 안 함 |
| `representative_menu` | 대표 메뉴라고 명시된 것만 저장 |
| `episode_number` | 회차로 명시된 값 |

모든 필드는 `value`, `status`, `evidence`, `source_url`을 가집니다. 누락/모순 시 `확인 필요`, 자동 추출은 `extracted_needs_review`, 사람 승인 후만 `human_verified`입니다. 루트 `program`, `category`는 추출 필드에서 만든 편의 값이며 별도 검증을 뜻하지 않습니다. `official_source_url`과 필드별 출처 URL을 유지합니다.

**스페셜 제목에 있는 날짜·일반 방송일·목록 날짜를 원방송일이나 재방송일로 임의 대입하지 않습니다.** 스페셜이라는 이름만으로 재방송 여부를 예로 확정하지도 않습니다. 코너별 원방송일을 별도로 처리하며, 재방송일보다 늦은 원방송일 등 모순된 날짜는 확인 필요로 처리합니다. 일반 방송일과 명시 원방송일이 충돌하면 `broadcast_date`는 확인 필요로 남깁니다.

명시 라벨·본문 블록·2열 표·inline span 형태를 합성 HTML로 검증했습니다. 라벨 없는 임의 문장, JavaScript 렌더링, 실제 사이트 고유 DOM에 대한 대응은 미검증입니다. 메타데이터가 본문 밖에 있거나 지원하지 않는 구조라면 추측하지 않고 누락/경고로 남깁니다. 기존 JSON을 읽어 CSV/Markdown으로 내보낼 때 새 필드가 없으면 확인 필요로 처리합니다. 새 파싱의 ID에는 코너/원방송일도 반영되므로 과거 파싱 ID와 달라질 수 있고, 과거 검토 파일은 같은 과거 records 파일과 쌍으로 사용해야 합니다.


## 초기 실제 조사·실행 결과

2026-10-19 KST, Python 3.12.14에서 실행했습니다.

| 항목 | 관찰 결과 | 판단 범위 |
| --- | --- | --- |
| 프로그램 홈페이지 후보 | `https://program.kbs.co.kr/2tv/culture/reallive/pc/index.html` 요청 시 프록시 `CONNECT 403` | 현재 URL 유효성·HTML·메뉴·회차 미확인 |
| 공식 편성표 후보 | `https://schedule.kbs.co.kr/`의 robots 접근 실패 | 편성표 제공 형식·방송일 미확인 |
| KBS 홈페이지 | `https://www.kbs.co.kr/robots.txt` 프록시 차단 | 약관·저작권 안내 미확인 |
| 게시판 호스트 후보 | `https://pbbs.kbs.co.kr/robots.txt` 프록시 차단 | 게시판 경로·API 계약 미확인 |
| API 호스트 후보 | `https://apis.kbs.co.kr/robots.txt` 프록시 차단 | 공개 API 존재·인증·이용 조건 미확인 |
| `tvblog probe` | 5개 호스트 모두 `ProxyError`, 종료 코드 2 | [실제 접근 보고서](docs/results/live-probe-2026-10-19/report.json) |
| `tvblog collect --count 5` | `blocked`, 선택 0회, 성공 0회, 식당 0건, 종료 코드 2 | [실제 수집 보고서](docs/results/live-five-2026-10-19/report.json) |
| 합성 HTML → JSON/CSV/Markdown | 가상 식당 2건 처리, 종료 코드 0 | [합성 결과](docs/results/synthetic-demo/records.json), **실제 방송 자료 아님** |
| 자동 테스트 | 31개 통과 | 파서·정책·수집 실패·5개 날짜 선택·내보내기·검토 흐름; 라이브 수집 통과를 의미하지 않음 |

초기 조사 당시 환경 설정은 패키지 관리자 도메인을 허용하는 제한 네트워크였습니다. 직접 HTTPS 점검에서 `CONNECT tunnel failed, response 403`을 확인했습니다. 이는 **KBS 원본 서버의 HTTP 403이나 robots 금지 판정을 받은 것이 아닙니다.** 수집 프로그램은 robots를 확인하지 못하면 본문 요청을 중단합니다. 차단을 우회하지 않았습니다.

실제 결과 디렉터리에는 `records.json`의 빈 배열, 헤더만 있는 `records.csv`, `report.json`이 있습니다. 실제 정보가 없으므로 식당 5건을 만들어 채우거나 가짜 블로그 초안을 생성하지 않았습니다. `docs/results/synthetic-demo`는 합성 자료만 포함하며 라이브 결과와 분리되어 있습니다.

### 확인된 사실과 미확인 사항

- **확인됨:** 패키지 설치·CLI 실행·테스트·출력 기능, 현재 환경의 프록시 차단. 합성 자료는 합성 fixture와의 일치만 확인했습니다.
- **미확인:** 최근 실제 5회 방송 날짜/회차, 실제 상호/주소/대표 메뉴, 운영 중인 정확한 방송정보 URL, 실제 DOM, 공개 API 제공 여부, KBS별 수집·재이용 약관.
- **추정값:** 데이터에 넣지 않습니다. 게시일을 방송일로, 일반 메뉴를 대표 메뉴로, 평일을 실제 방송일로 바꾸지 않습니다. 후보 URL은 검증된 수집 경로로 취급하지 않습니다.

## 로컬 설치

Python 3.11 이상이 필요합니다. 이 환경에서는 3.12로 검증했으며 3.11 실행 자체는 아직 검증하지 않았습니다.

```bash
python3 -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
python -m pytest -q
```

`requirements.lock`은 이번 검증에서 사용한 런타임·테스트 패키지의 정확한 버전 목록입니다. 프로젝트 자체의 의존성 범위는 `pyproject.toml`에 있습니다. 빌드 도구는 pip의 격리 빌드로 설치합니다. TLS 검증을 끄는 옵션은 사용하지 않습니다.

### 네트워크 조사와 최근 5개 방송 날짜 수집

```bash
tvblog probe --out outputs/probe
tvblog collect --count 5 --out outputs/recent-five
```

기본 수집기는 프로그램 홈 후보의 실제 HTML에서 `방송정보` 링크를 발견해야 진행합니다. 링크가 동적이거나 여러 개면 추측하지 않고 `needs_listing_url`로 멈춥니다. 공식 홈페이지에서 확인한 실제 방송정보 목록 URL을 지정할 수 있습니다.

```bash
tvblog collect --listing-url '공식 페이지에서 확인한 HTTPS 목록 URL' --count 5 --out outputs/confirmed-list
```

현재 KBS DOM으로 검증되지 않았기 때문에 위 명령이 실제 데이터를 얻는다고 보장하지 않습니다. 상세 페이지는 `.board-view-contents`, `.board-view-content`, `.view_cont`, `.view-content`, `.bbs_view_cont`, `article`, `main` 중 본문 컨테이너를 사용합니다. `상호:`, `상호명:`, `식당명:`, `주소:`, `대표 메뉴:` 등 명시 라벨만 지원합니다. 라벨 없는 `▶ 가게명` 같은 형식이나 라벨/값이 별도 요소인 형식은 실제 문서를 확인한 뒤 어댑터와 회귀 fixture를 추가해야 합니다. 현재는 명시 라벨이 있는 식당·여행지·숙소 등의 장소 필드를 지원하며, 레시피 전용 추출은 후속 범위입니다.

목록은 명시적 다음 페이지 링크를 따라 최대 3페이지까지만 읽습니다. **제목에 연·월·일과 `방송정보`가 있는 글**에서 현재 한국 날짜 이하의 서로 다른 방송 날짜 최대 5개를 선택합니다. 같은 날짜의 여러 게시물은 1회로 묶습니다. 목록 게시일, 연도가 없는 제목, 미래 날짜는 선택 근거로 사용하지 않습니다. 본문에 방송일이 있으면 목록과 대조하며 충돌 시 제외합니다.

이 제한된 목록 범위만으로 전체 사이트의 최신성을 보장할 수 없어 `latest_five_verified`는 `false`입니다. 접근이 복구되면 실제 목록 정렬·고정 공지·누락·결방·회차를 확인하고 실제 최근 5회 여부를 별도로 대조해야 합니다. 일부 음식점만 파싱됐을 가능성도 있어 `successful_episode_count`는 본문에서 1건 이상 추출한 날짜 수이며, 그 방송의 모든 장소를 수집했다는 뜻은 아닙니다.

종료 코드는 `0`: 해당 작업 완료(추출은 검토 대기), `1`: 입력/로컬 오류, `2`: 차단·미지원 구조·부분 수집입니다. `collect`가 0이어도 최신 5회 또는 모든 필드의 사실 검증 완료를 뜻하지 않습니다. 기존 출력 디렉터리는 덮어쓰지 않으므로 재실행 시 새 `--out` 경로를 사용하세요.

### 허용된 HTML로 오프라인 실행

공식 페이지를 정상적으로 열 수 있고 이용 조건이 허용할 때만 사용자가 직접 저장한 UTF-8 HTML을 처리할 수 있습니다. 네트워크 우회 기능이 아닙니다. manifest와 HTML을 같은 디렉터리에 두세요.

```json
{
  "sources": [
    {"file": "broadcast.html", "source_url": "https://program.kbs.co.kr/실제로-확인한-원문-경로"}
  ]
}
```

```bash
tvblog import-html --manifest /path/to/allowed/manifest.json --out outputs/imported
```

제공 HTML의 원격 진위·최신성은 자동 검증할 수 없어 `source_mode=provided_html`로 기록합니다. 실제 방송일은 본문의 명시 라벨에서만 추출합니다. 합성 데모는 아래 명령으로 재현할 수 있습니다.

```bash
tvblog import-html --manifest tests/fixtures/manifest.json --fixture --out outputs/demo
tvblog review-template --records outputs/demo/records.json --out outputs/demo/review.json
```

합성 자료의 주소·회차·상호·원문 URL은 모두 테스트용이며 실재하지 않습니다. 합성 자료를 실제 방송정보처럼 게시하면 안 됩니다.

## 데이터와 블로그 검토

출력은 `report.json`, `records.json`, UTF-8 BOM의 `records.csv`, `drafts/<id>.md`입니다. JSON/CSV에는 값뿐 아니라 각 필드의 `status`, 짧은 `evidence`, `source_url`과 수집 시각이 들어갑니다. 전체 방송 본문·사진·영상은 저장하지 않습니다. CSV는 스프레드시트 수식 주입을 방지하기 위해 위험한 셀 앞에 `'`를 붙입니다. JSON은 원래 값을 보존합니다.

| 상태 | 의미 | 블로그 본문 반영 |
| --- | --- | --- |
| `missing` | 자료 없음/충돌, 값 `확인 필요` | `확인 필요` |
| `extracted_needs_review` | 명시 라벨에서 추출, 원문 대조 필요 | `확인 필요` |
| `human_verified` | 사람이 원문과 추출값·근거를 대조해 승인 | 승인 값만 사용 |

`official_source_url`은 라이브 요청 URL 또는 사용자가 선언한 원문 URL입니다. URL을 기록한 것만으로 원문을 검증했다고 간주하지 않습니다. `additional_sources`는 실제로 사람이 추가 대조한 URL·내용·필드를 기록합니다. 추가 확인이 없으면 빈 배열과 `independent_confirmation=확인 필요`를 유지합니다.

```bash
tvblog review-template --records outputs/recent-five/records.json --out outputs/review.json
# 원문을 직접 대조하고 review.json의 reviewer와 승인할 필드별 note를 작성합니다.
# 승인하지 않을 필드는 fields에서 삭제합니다. 빈 note로는 승인되지 않습니다.
tvblog review --records outputs/recent-five/records.json --decisions outputs/review.json --out outputs/reviewed
```

검토 파일에서 `expected_value`, `evidence`는 추출 결과와 정확히 일치해야 합니다. 승인한 필드만 Markdown에 반영됩니다. 추가 출처를 확인했다면 각 records 항목에 다음 구조를 넣습니다. 외부 사이트를 자동 요청하는 기능은 아직 없으며 **사람의 대조 기록**입니다.

```json
{
  "additional_sources": [
    {
      "url": "https://실제로-확인한-업장-공식-출처",
      "fields": ["address"],
      "note": "실제로 확인한 내용과 확인 시점을 기록"
    }
  ]
}
```

시스템이 인간 검토의 진실성을 보증하지는 않습니다. `publication_ready`는 항상 false이며 게시 여부는 별도 판단입니다. 초안은 검색에 필요한 방송일·식당명·주소·대표 메뉴·출처 중심의 짧은 정리입니다. 허위 방문 후기·맛 평가·검색량 추정·추천 순위·확인하지 않은 영업시간/가격은 생성하지 않습니다.

## 접근 복구와 허용된 대안

1. 클라우드 환경 설정 초안에 `program.kbs.co.kr`, `www.kbs.co.kr`, `schedule.kbs.co.kr`, `pbbs.kbs.co.kr`, `apis.kbs.co.kr`를 추가했습니다. **환경 설정에서 검토·저장한 뒤 환경을 게시**해야 활성화할 수 있습니다. 초안 저장만으로 이번 실행 환경의 요청이 허용되거나 배포된 것은 아닙니다. 기존 패키지 관리자 프리셋은 보존했습니다.
2. 접근 가능한 환경에서 `probe`를 새 결과 경로로 실행하고 robots·이용약관·저작권 안내와 실제 방송정보 메뉴를 확인합니다. 허용을 확인한 페이지에서 `collect`를 실행하고 최근 실제 5회 날짜와 추출 정확성을 대조합니다. DNS/프록시를 우회하거나 인증 차단을 피해 수집하지 마세요.
3. 실제 HTML이 JavaScript 렌더링에 의존하면, 정상 브라우저에서 공식 페이지가 사용하는 공개 요청과 이용 조건을 확인합니다. 허용된 경우에 한해 Playwright/공식 JSON 어댑터를 추가할 수 있습니다. 현재는 Playwright를 도입하지 않았으며 네트워크 CONNECT 차단을 해결하는 용도로 사용하지 않습니다. 로그인·캡차·유료 자료는 자동 접근하지 않습니다.
4. **공식 API는 존재 여부와 제공 범위를 확인하지 못했습니다.** `apis.kbs.co.kr`라는 후보 호스트를 공개 API 계약으로 간주하지 않습니다. KBS/프로그램 담당 부서에 방송정보 텍스트 제공·재이용 허락과 문서화된 API/피드 제공 여부를 문의하는 방법이 있습니다. 실제 제공받기 전에는 엔드포인트나 API 키를 만들어 쓰지 않습니다.
5. 정상 공개된 공식 HTML을 이용 조건에 맞게 직접 저장해 import하거나, KBS가 허용한 공식 피드/자료 제공을 이용하는 방식이 대안입니다. 제3자 블로그 재수집, 검색 캐시, 비공식 미러를 차단 우회 수단으로 사용하지 않습니다.

## 저작권·수집 정책

robots 허용은 콘텐츠 재이용 허락과 다릅니다. 이번 환경에서는 약관/robots를 읽지 못했으므로 법적 이용 허락을 확인했다고 주장하지 않습니다. 실제 운영 전 개별 사이트 정책·허락을 확인해야 합니다. 프로그램은 공개 사실의 최소 요약과 짧은 근거만 저장하고 출처를 남깁니다. 방송 캡처·사진·동영상 다운로드, 원문 전문 복제, 원문 스타일을 모사한 재작성은 하지 않습니다.

요청은 식별 가능한 `TVBlogResearch/0.1` User-Agent, 최소 2초 간격, 사이트가 더 긴 간격을 요구하면 그 간격을 적용합니다. 사이트별 robots를 먼저 확인하고 불가/불명확 상태에서 중단합니다. 401/403/429/5xx는 자동 반복/우회하지 않습니다. HTTPS와 인증서 검증을 유지하고, 리디렉션도 허용된 KBS 호스트와 목적지 robots를 확인합니다. 외부 출처는 자동으로 따라가지 않습니다.

## 구조와 확장

```text
src/tvblog/
  http.py       HTTPS·robots·속도 제한·요청 감사
  parser.py     HTML → 명시 사실/근거 (KBS DOM 라이브 검증 대기)
  collector.py  공식 링크 탐색·목록/날짜 선택·부분 실패 보고
  models.py     사실 상태·안정 ID
  review.py     원문 대조 승인·추가 출처 기록
  export.py     JSON/CSV·검증 필드만 Markdown 반영
  diagnostics.py  프록시 변수 존재 여부·DNS/CONNECT/TLS/HTTP 단계 진단
  cli.py        diagnose / probe / collect / import-html / review-template / review
```

DB 없이 파일로 작동하며 PostgreSQL을 도입할 때 `records`/`facts`/`sources`를 저장소 계층으로 분리할 수 있습니다. 서버에서는 요청 시 장시간 실행하는 웹 서버보다 **Cloud Run Jobs 같은 배치 작업**으로 CLI를 실행하는 구성이 적합합니다. 컨테이너, Cloud Storage 결과 업로드, Cloud Scheduler, PostgreSQL 마이그레이션, 실제 클라우드 배포는 이번 구현에 포함하지 않았습니다. Cloud Run의 임시 파일시스템에 결과를 영구 보관할 수 없으므로 서버 배포 전 저장소 연동이 필요합니다.

장기 운영은 검증된 본문 샘플 확보 → DOM/API 어댑터 확정 → 실제 최근 5회 회귀 검증 → 허용된 추가 출처 연동 → 배치 배포 순서로 진행하면 됩니다.
