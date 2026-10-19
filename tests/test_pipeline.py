import csv
import json
from datetime import date
from pathlib import Path

import pytest

from tvblog.cli import main
from tvblog.collector import collect
from tvblog.export import export_run, render_draft
from tvblog.http import AccessError
from tvblog.parser import parse_detail
from tvblog.review import apply_review

FIXTURES = Path(__file__).parent / "fixtures"
URL = "https://program.kbs.co.kr/__synthetic_fixture__/detail.html"


def rows():
    return parse_detail((FIXTURES / "detail.html").read_text(), URL, "synthetic_fixture")[0]


def test_unreviewed_values_never_appear_as_blog_facts():
    draft = render_draft(rows()[0])
    assert "가상식당 알파" not in draft
    assert "테스트시 가상로 0" not in draft
    assert "식당 이름: 확인 필요" in draft
    assert "합성 테스트" in draft


def test_human_review_matches_exact_fact_then_can_render(tmp_path):
    data = rows()
    f = data[0]["facts"]["name"]
    decisions = {"reviewer": "합성 테스트 검토자", "records": [{"id": data[0]["id"], "fields": {
        "name": {"expected_value": f["value"], "evidence": f["evidence"], "note": "합성 fixture 원문 대조"}},
        "additional_sources": [{"url": "https://example.org/synthetic", "fields": ["name"], "note": "합성 검토 데이터"}]}]}
    reviewed = apply_review(data, decisions)
    assert data[0]["facts"]["name"]["status"] == "extracted_needs_review"
    assert reviewed[0]["facts"]["name"]["status"] == "human_verified"
    assert "가상식당 알파" in render_draft(reviewed[0])
    assert "테스트시 가상로 0" not in render_draft(reviewed[0])
    assert reviewed[0]["publication_ready"] is False
    decisions["records"][0]["fields"]["name"]["expected_value"] = "다른 값"
    with pytest.raises(ValueError):
        apply_review(data, decisions)


def test_csv_json_exports_and_formula_safety(tmp_path):
    data = rows()
    data[0]["facts"]["name"]["value"] = "  =HYPERLINK(1)"
    out = tmp_path / "run"
    export_run(out, {"status": "synthetic"}, data)
    exported = json.loads((out / "records.json").read_text())
    assert len(exported) == 2
    with (out / "records.csv").open(encoding="utf-8-sig") as stream:
        table = list(csv.DictReader(stream))
    assert table[0]["name_value"].startswith("'")
    assert len(list((out / "drafts").glob("*.md"))) == 2
    with pytest.raises(FileExistsError):
        export_run(out, {}, [])


class FakeClient:
    audit = []

    def __init__(self, pages):
        self.pages, self.calls = pages, []

    def get_html(self, url):
        self.calls.append(url)
        if url not in self.pages:
            raise AccessError("proxy_error", url, "ProxyError")
        return self.pages[url]


def test_five_distinct_synthetic_dates_and_duplicate_day():
    listing = "https://program.kbs.co.kr/list"
    # Deliberately unsorted to verify date-based selection; two posts on same day.
    days = [1, 5, 3, 6, 2, 4]
    links = ''.join(f'<a href="/d{d}">2026-01-{d:02} 방송정보</a>' for d in days)
    links += '<a href="/extra">2026-01-06 방송정보</a>'
    pages = {listing: links}
    for d in days:
        pages[f"https://program.kbs.co.kr/d{d}"] = f'<article>방송일: 2026-01-{d:02}<br>상호: 합성{d}<br>주소: 합성주소</article>'
    pages["https://program.kbs.co.kr/extra"] = '<article>방송일: 2026-01-06<br>상호: 합성추가</article>'
    report, records = collect(FakeClient(pages), listing, 5, date(2026, 1, 10))
    assert report["selected_episode_count"] == report["successful_episode_count"] == 5
    assert report["status"] == "collected_needs_review"
    assert len(records) == 6
    assert {r["facts"]["broadcast_date"]["value"] for r in records} == {f"2026-01-{d:02}" for d in [2, 3, 4, 5, 6]}
    assert report["latest_five_verified"] is False


def test_blocked_does_not_invent_five_empty_episodes():
    report, records = collect(FakeClient({}), None)
    assert report["status"] == "blocked"
    assert report["selected_episode_count"] == report["successful_episode_count"] == 0
    assert records == []


def test_single_failed_detail_makes_run_incomplete():
    listing = "https://program.kbs.co.kr/list"
    pages = {listing: '<a href="/missing">2026-01-01 방송정보</a>'}
    report, records = collect(FakeClient(pages), listing, 1, date(2026, 1, 2))
    assert report["status"] == "incomplete"
    assert report["selected_episode_count"] == 1
    assert report["successful_episode_count"] == 0
    assert not records


def test_cli_import_and_template_preserve_existing_results(tmp_path):
    out = tmp_path / "run"
    assert main(["import-html", "--manifest", str(FIXTURES / "manifest.json"), "--fixture", "--out", str(out)]) == 0
    assert json.loads((out / "report.json").read_text())["mode"] == "synthetic_fixture"
    assert main(["import-html", "--manifest", str(FIXTURES / "manifest.json"), "--fixture", "--out", str(out)]) == 1
    decisions = tmp_path / "decisions.json"
    assert main(["review-template", "--records", str(out / "records.json"), "--out", str(decisions)]) == 0
    assert json.loads(decisions.read_text())["reviewer"] == ""
    assert main(["review", "--records", str(out / "records.json"), "--decisions", str(decisions), "--out", str(tmp_path / "reviewed")]) == 1


def test_fixture_cannot_be_imported_as_live(tmp_path):
    assert main(["import-html", "--manifest", str(FIXTURES / "manifest.json"), "--out", str(tmp_path / "run")]) == 1
