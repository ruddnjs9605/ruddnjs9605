# 실제 공식 HTML 1건을 제공하는 방법

이 디렉터리에는 실제 HTML이 없습니다. manifest.example.json은 파일/URL 매핑 형식 예시이며 11344 페이지 내용이나 이용 허락을 검증했다는 뜻이 아닙니다.

1. 정상적으로 접근할 수 있는 공개 KBS 상세 페이지에서 robots, 이용약관, 데이터 재이용 조건을 확인합니다. 허용되는 범위에서만 저장/제공하세요. 허락이 불명확하면 먼저 확인해야 하며 자동 요청을 늘리지 않습니다.
2. 실제 방송 본문을 표시한 상태에서 브라우저의 저장(Ctrl+S 또는 Cmd+S) 기능으로 **HTML만** 저장하고 `broadcast.html`로 이름을 정합니다. 이미지/영상 파일은 필요하지 않습니다. URL만, PDF, 화면 캡처로는 DOM을 검증할 수 없습니다.
3. 화면에는 본문이 있는데 저장 파일에 없으면, 정책상 허용되는 경우에만 개발자도구 Elements에서 `html` 노드의 Copy → Copy outerHTML로 **현재 표시된 DOM**을 복사해 UTF-8 HTML로 저장할 수 있습니다. 이는 사용자 브라우저에서 정상 표시된 공개 문서의 수동 제공이며, 서버 접근·인증·네트워크 차단 우회 기능이 아닙니다. import는 JavaScript를 실행하거나 외부 파일을 요청하지 않습니다.
4. 예시 manifest를 복사하고, 브라우저 주소창의 **최종 실제 원문 URL**, 정확한 파일명, 저장 시각, 저장 방식과 직접 확인한 이용 조건을 작성합니다. UTF-8 이외에 CP949/EUC-KR 파일이면 encoding을 `cp949`/`euc-kr`로 지정합니다. 인코딩을 자동 추측하지 않습니다.
5. 이 채팅에 `broadcast.html`을 첨부하고 실제 원문 URL을 함께 전달하면 됩니다. manifest도 작성했다면 함께 첨부하세요. 이 앱의 첨부 버튼 위치는 현재 제가 볼 수 없으므로 정확한 UI 위치는 안내할 수 없습니다. 한 파일만 먼저 제공하면 됩니다. 압축을 풀 때 임의 실행파일이나 외부 에셋은 필요하지 않습니다.

클라우드에 파일이 준비됐다면 아래 폴더 구성을 사용합니다.

```text
/workspace/ruddnjs9605/inputs/kbs-one/
  broadcast.html
  manifest.json
```

```bash
cd /workspace/ruddnjs9605
.venv/bin/tvblog import-html --manifest inputs/kbs-one/manifest.json --out outputs/kbs-one-01
.venv/bin/tvblog review-template --records outputs/kbs-one-01/records.json --out outputs/kbs-one-review.json
```

입력 HTML의 해시, 인코딩, byte 수, 사용자 선언 출처, DOM 구조 통계, 파싱 경고는 `report.json`에 저장합니다. 전체 본문, 스크립트 코드, iframe 주소는 구조 요약에 복제하지 않습니다. 본문 컨테이너 미식별/추출 0건은 `unparsed`와 종료 코드 2입니다. 파일을 읽었다는 사실을 실사이트 검증 성공으로 처리하지 않습니다.

## 원문 대조용 기대값 비교

한 페이지에서 확인한 첫 장소를 검증하려면 해당 source에 `expected_records`를 넣습니다. 아래 값은 **실제 정보가 아니며**, 각 값을 제공한 원문에서 확인한 값으로 바꿔야 합니다. 원문에 없으면 문자열 `확인 필요`를 넣으세요. `record_index`는 0부터 시작하는 추출 순서입니다.

```json
"expected_records": [
  {
    "record_index": 0,
    "facts": {
      "program_name": "원문에서 확인한 프로그램명",
      "broadcast_date": "원문에서 확인한 원방송 기준 날짜 또는 확인 필요",
      "posted_date": "원문에서 확인한 게시일 또는 확인 필요",
      "corner_name": "원문에서 확인한 코너명 또는 확인 필요",
      "place_type": "원문에서 확인한 유형 또는 확인 필요",
      "name": "원문에서 확인한 장소명",
      "introduced_menu": "원문에서 확인한 음식/메뉴 또는 확인 필요",
      "address": "원문에서 확인한 주소 또는 확인 필요"
    }
  }
]
```

날짜는 추출 JSON과 같은 `YYYY-MM-DD` 형식으로 적습니다. 원방송일과 재방송일을 분리하려면 `original_broadcast_date`, `rebroadcast_date`, `is_rebroadcast`도 추가하세요. 값과 근거를 동시에 비교하려면 필드 값을 `{"value": "확인한 값", "evidence": "파서가 기록해야 하는 정확한 원문 근거"}`로 작성할 수 있습니다.

같은 import 명령을 **새 출력 폴더**로 실행하면 비교 결과도 report에 저장합니다.

```bash
.venv/bin/tvblog import-html --manifest inputs/kbs-one/manifest.json --out outputs/kbs-one-02
```

- `matched`: 지정한 8개 핵심 필드 전부에 대한 기대값 일치
- `partial_match`: 지정한 일부 필드 기대값만 일치
- `failed`: 값/근거 불일치 또는 지정한 장소 순번 없음 → 작업 상태 `expectation_failed`, 종료 코드 2
- `not_requested`: 기대값 없음 → 파싱 결과만 생성, 검증 성공 주장 없음

`matched`는 제공한 기대값과 일치한다는 의미이며, 기대값 자체의 정확성·원격 진위·사용 허락·독립 검증을 보증하지 않습니다. 모든 사실은 기존 `extracted_needs_review`를 유지합니다. 실제 원문과 대조한 뒤 별도 `review`로 승인해야 Markdown에 반영됩니다.

```bash
# 위 review-template 파일에 원문 대조 후 reviewer와 승인 필드별 note를 작성합니다.
.venv/bin/tvblog review --records outputs/kbs-one-01/records.json --decisions outputs/kbs-one-review.json --out outputs/kbs-one-reviewed
```

기존 범용 파서로 못 읽는 DOM이면 보고서를 토대로 실제 문서 전용 어댑터가 필요할 수 있습니다. **테스트 시작은 현재 CLI로 가능하지만, 아직 확보하지 못한 실제 DOM의 파싱 성공을 보장하지는 않습니다.** 실제 1건을 사람이 검증하기 전에는 최근 5회로 확대하지 않습니다.
