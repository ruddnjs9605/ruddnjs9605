"""SYNTHETIC cases only: not evidence of live KBS compatibility."""
from datetime import date
from pathlib import Path

from tvblog.models import FIELDS, UNKNOWN
from tvblog.parser import listing_entries, parse_detail

URL = "https://iaudience.kbs.co.kr/__synthetic_fixture__/special"
FIXTURE = Path(__file__).parent / "fixtures/synthetic/special.html"


def parse(text):
    return parse_detail(f"<article>{text}</article>", URL, "synthetic_fixture")


def test_special_dates_posted_date_and_corners_are_separate():
    records, warnings = parse_detail(FIXTURE.read_text(), URL, "synthetic_fixture")
    assert len(records) == 2
    one, two = (r["facts"] for r in records)
    assert one["program_name"]["value"] == "생생정보 스페셜"
    assert one["posted_date"]["value"] == "2026-10-19"
    assert one["broadcast_date"]["value"] == one["original_broadcast_date"]["value"] == "2026-09-01"
    assert two["broadcast_date"]["value"] == "2026-08-02"
    assert one["rebroadcast_date"]["value"] == two["rebroadcast_date"]["value"] == "2026-10-18"
    assert one["is_rebroadcast"]["value"] == "예"
    assert one["corner_name"]["value"] == "합성 맛집 코너"
    assert two["corner_name"]["value"] == "합성 여행 코너"
    assert one["place_type"]["value"] == "식당"
    assert two["place_type"]["value"] == "여행지"
    assert records[1]["category"] == "travel_site"
    assert one["introduced_menu"]["value"] == "가상 국수"
    assert one["representative_menu"]["value"] == UNKNOWN
    assert one["address"]["value"] == "가상시 합성로 0"
    assert all(f["status"] in ("missing", "extracted_needs_review") for r in records for f in r["facts"].values())
    assert any("추정하지 않음" in warning for warning in warnings)


def test_special_without_original_date_never_uses_listing_or_generic_date():
    records, warnings = parse_detail('<article><h1>생생정보 스페셜</h1>방송일: 2026-10-18<br>게시일: 2026-10-19<br>상호: 합성</article>', URL,
                                     listing={"broadcast_date": "2026-10-18", "date_evidence": "2026-10-18 생생정보 스페셜 방송정보"})
    f = records[0]["facts"]
    assert f["broadcast_date"]["value"] == UNKNOWN
    assert f["original_broadcast_date"]["value"] == UNKNOWN
    assert f["rebroadcast_date"]["value"] == UNKNOWN
    assert f["is_rebroadcast"]["value"] == UNKNOWN  # special alone is not proof of rerun
    assert warnings


def test_document_title_special_guard_without_heading():
    records, _ = parse_detail('<title>생생정보 스페셜</title><article>방송일: 2026-10-18<br>상호: 합성</article>', URL)
    assert records[0]["facts"]["broadcast_date"]["value"] == UNKNOWN


def test_missing_program_type_menu_and_rerun_are_not_defaulted():
    records, _ = parse("상호: 합성상호")
    r = records[0]
    assert r["program"] == r["category"] == UNKNOWN
    assert set(r["facts"]) == set(FIELDS)
    for field in ("program_name", "place_type", "introduced_menu", "is_rebroadcast", "posted_date"):
        assert r["facts"][field]["value"] == UNKNOWN
        assert r["facts"][field]["status"] == "missing"


def test_posted_date_does_not_become_broadcast_date():
    records, _ = parse("등록일: 2026-10-19<br>숙소명: 합성 숙소<br>주소: 가상주소")
    assert records[0]["facts"]["posted_date"]["value"] == "2026-10-19"
    assert records[0]["facts"]["broadcast_date"]["value"] == UNKNOWN
    assert records[0]["category"] == "accommodation"


def test_type_and_menu_do_not_leak_between_places():
    records, _ = parse("장소명: 첫 장소<br>장소 유형: 식당<br>대표 메뉴: 합성 메뉴<br>장소명: 두번째 장소")
    assert records[0]["facts"]["place_type"]["value"] == "식당"
    assert records[1]["facts"]["place_type"]["value"] == UNKNOWN
    assert records[1]["facts"]["introduced_menu"]["value"] == UNKNOWN


def test_multiple_introduced_dishes_do_not_imply_representative_menu():
    records, _ = parse("식당명: 합성<br>소개 음식: 합성 A<br>소개 메뉴: 합성 B")
    assert records[0]["facts"]["introduced_menu"]["value"] == "합성 A / 합성 B"
    assert records[0]["facts"]["representative_menu"]["value"] == UNKNOWN


def test_date_order_conflict_and_explicit_nonrerun_conflict():
    records, warnings = parse("원방송일: 2026-10-19<br>재방송일: 2026-10-18<br>장소명: 합성")
    for field in ("broadcast_date", "original_broadcast_date", "rebroadcast_date"):
        assert records[0]["facts"][field]["value"] == UNKNOWN
    assert warnings
    records, warnings = parse("재방송 여부: 아니오<br>재방송일: 2026-10-18<br>장소명: 합성")
    assert records[0]["facts"]["is_rebroadcast"]["value"] == UNKNOWN
    assert warnings


def test_normal_original_date_conflict_does_not_get_healed_from_listing():
    records, warnings = parse_detail('<article>방송일: 2026-10-18<br>원방송일: 2026-10-17<br>상호: 합성</article>', URL,
                                     listing={"broadcast_date": "2026-10-18", "date_evidence": "test"})
    assert records[0]["facts"]["broadcast_date"]["value"] == UNKNOWN
    assert warnings


def test_invalid_or_ambiguous_date_is_not_replaced_by_first_date():
    records, warnings = parse("방송일: 2026-10-17 / 2026-10-18<br>상호: 합성")
    assert records[0]["facts"]["broadcast_date"]["value"] == UNKNOWN
    assert warnings


def test_table_labels_and_inline_spans():
    records, _ = parse('<table><tr><th>프로그램명</th><td>생생정보</td></tr><tr><th>방송일</th><td>2026-10-16</td></tr></table><p><b>장소명:</b> <span>합성 장소</span></p>')
    assert records[0]["facts"]["program_name"]["value"] == "생생정보"
    assert records[0]["facts"]["broadcast_date"]["value"] == "2026-10-16"
    assert records[0]["facts"]["name"]["value"] == "합성 장소"


def test_special_listings_are_not_counted_as_new_regular_broadcasts():
    html = '<a href="/broadcast/1">2026-10-18 생생정보 스페셜 방송정보</a><a href="/broadcast/2">2026-10-16 생생정보 방송정보</a>'
    html += '<a href="/broadcast/3">2026-10-14 / 2026-10-15 방송정보</a>'
    entries = listing_entries(html, URL, date(2026, 10, 19))
    assert [entry["broadcast_date"] for entry in entries] == ["2026-10-16"]


def test_source_and_evidence_exist_for_every_extracted_field():
    records, _ = parse_detail(FIXTURE.read_text(), URL, "synthetic_fixture")
    for r in records:
        assert r["official_source_url"] == URL
        for f in r["facts"].values():
            if f["status"] == "extracted_needs_review":
                assert f["source_url"] == URL and f["evidence"]


def test_place_specific_original_dates_do_not_leak_in_special():
    rows, _ = parse('<h1>생생정보 스페셜</h1>재방송일: 2026-10-18<br>식당명: 합성 A<br>원방송일: 2026-09-01<br>식당명: 합성 B<br>원방송일: 2026-08-02<br>식당명: 합성 C')
    assert [r["facts"]["broadcast_date"]["value"] for r in rows] == ["2026-09-01", "2026-08-02", UNKNOWN]
    assert all(r["facts"]["rebroadcast_date"]["value"] == "2026-10-18" for r in rows)
