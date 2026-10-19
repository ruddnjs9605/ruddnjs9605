from datetime import date
from pathlib import Path

from tvblog.models import UNKNOWN
from tvblog.parser import listing_entries, parse_date, parse_detail

URL = "https://program.kbs.co.kr/__synthetic_fixture__/detail.html"
HTML = (Path(__file__).parent / "fixtures/detail.html").read_text()


def test_labels_provenance_and_missing_menu():
    rows, warnings = parse_detail(HTML, URL, "synthetic_fixture")
    assert not warnings
    assert len(rows) == 2
    assert rows[0]["facts"]["name"]["value"] == "가상식당 알파"
    assert rows[0]["facts"]["broadcast_date"]["value"] == "2026-01-02"
    assert rows[0]["facts"]["address"]["evidence"] == "주소: 테스트시 가상로 0"
    assert rows[0]["facts"]["address"]["source_url"] == URL
    assert rows[1]["facts"]["representative_menu"]["value"] == UNKNOWN
    assert rows[0]["additional_sources"] == []
    assert rows[0]["publication_ready"] is False


def test_does_not_guess_names_or_dates():
    rows, warnings = parse_detail("<article>2026-01-02 게시<br>맛있는 식당<br>주소: 서울</article>", URL)
    assert rows == [] and warnings
    rows, _ = parse_detail("<article>게시일: 2026-01-02<br>상호: 가상식당</article>", URL)
    assert rows[0]["facts"]["broadcast_date"]["value"] == UNKNOWN


def test_conflict_or_unknown_body_fails_closed():
    rows, warnings = parse_detail("<div>상호: X</div>", URL)
    assert rows == [] and warnings
    rows, warnings = parse_detail("<article>상호: X<br>주소: A<br>주소: B</article>", URL)
    assert rows[0]["facts"]["address"]["value"] == UNKNOWN and warnings
    rows, warnings = parse_detail(HTML, URL, listing={"broadcast_date": "2026-01-03", "date_evidence": "test"})
    assert not rows and warnings == ["목록과 본문의 방송일 불일치"]


def test_listing_ignores_posted_dates_missing_year_and_future():
    html = '''<table>
    <tr><td><a href="/one">2026년 1월 2일 방송정보</a></td><td>2026-01-03 게시</td></tr>
    <tr><td><a href="/one">2026년 1월 2일 방송정보</a></td></tr>
    <tr><td><a href="/two">방송정보</a></td><td>2026-01-01</td></tr>
    <tr><td><a href="/three">1월 1일 방송정보</a></td></tr>
    <tr><td><a href="/four">2027-01-01 방송정보</a></td></tr>
    <tr><td><a href="https://example.org/x">2026-01-01 방송정보</a></td></tr>
    </table>'''
    entries = listing_entries(html, URL, date(2026, 2, 1))
    assert len(entries) == 1
    assert entries[0]["broadcast_date"] == "2026-01-02"
    assert entries[0]["url"] == "https://program.kbs.co.kr/one"


def test_invalid_calendar_date():
    assert parse_date("2026-02-30 방송정보") is None


def test_regular_menu_is_not_a_representative_menu():
    rows, warnings = parse_detail("<article>상호: 합성식당<br>메뉴: 합성음식</article>", URL)
    assert rows[0]["facts"]["representative_menu"]["value"] == UNKNOWN
    assert warnings == ["일반 메뉴 라벨은 대표 메뉴로 추정하지 않음"]
