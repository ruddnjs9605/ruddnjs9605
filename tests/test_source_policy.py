from pathlib import Path

import pytest

from tvblog.cli import main
from tvblog.collector import IAUDIENCE_URLS, probe
from tvblog.http import AccessError, validate_url


def test_iaudience_urls_supported_for_allowed_html_import():
    assert all(validate_url(url) == url for url in IAUDIENCE_URLS)


def test_new_source_probe_does_not_fetch_content_or_repeat_origin_failure():
    class Fake:
        audit = []
        def __init__(self):
            self.policy_calls = []
        def get_html(self, url):
            assert "iaudience" not in url
            raise AccessError("proxy_error", url, "ProxyError")
        def check_policy(self, url):
            self.policy_calls.append(url)
            raise AccessError("proxy_error", "https://iaudience.kbs.co.kr/robots.txt", "ProxyError")
    client = Fake()
    report = probe(client)
    new = [e for e in report["events"] if "candidate_url" in e]
    assert len(new) == 4 and len(client.policy_calls) == 1
    assert all(e["content_requested"] is False and e["terms_permission"] == "unverified" for e in new)


def test_disallow_for_one_path_not_used_as_policy_for_every_path():
    class Fake:
        audit = []
        def get_html(self, url):
            raise AccessError("proxy_error", url, "ProxyError")
        def check_policy(self, url):
            if url.endswith("11344"):
                raise AccessError("robots_disallowed", url, "Disallow")
    events = [e for e in probe(Fake())["events"] if "candidate_url" in e]
    assert [e["outcome"] for e in events] == ["robots_allows_path", "robots_disallowed", "robots_allows_path", "robots_allows_path"]


def test_synthetic_special_import_writes_new_fields(tmp_path):
    import csv
    import json
    path = Path(__file__).parent / "fixtures/synthetic/manifest.json"
    out = tmp_path / "special"
    assert main(["import-html", "--manifest", str(path), "--fixture", "--out", str(out)]) == 0
    records = json.loads((out / "records.json").read_text())
    assert len(records) == 2
    assert records[0]["facts"]["original_broadcast_date"]["value"] != records[0]["facts"]["rebroadcast_date"]["value"]
    with (out / "records.csv").open(encoding="utf-8-sig") as stream:
        row = next(csv.DictReader(stream))
    assert row["posted_date_value"] == "2026-10-19"
    assert row["program_name_status"] == "extracted_needs_review"
    for draft in (out / "drafts").glob("*.md"):
        text = draft.read_text()
        assert "원방송 기준 방송일: 확인 필요" in text
        assert "재방송일: 확인 필요" in text
        assert "합성 테스트" in text


def test_legacy_json_can_still_be_exported(tmp_path):
    import json
    from tvblog.export import export_run
    path = Path(__file__).parents[1] / "docs/results/synthetic-demo/records.json"
    legacy = json.loads(path.read_text())
    assert "posted_date" not in legacy[0]["facts"]
    export_run(tmp_path / "legacy", {"status": "test"}, legacy)
    assert (tmp_path / "legacy/records.csv").exists()
