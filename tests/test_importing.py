"""Offline import regressions only; these do not validate any live KBS HTML."""
import hashlib
import json
from pathlib import Path

import pytest
import requests

from tvblog.cli import main
from tvblog.importing import CORE_FIELDS, compare_expectations, import_manifest, inspect_html
from tvblog.parser import parse_detail

FIXTURE = Path(__file__).parent / "fixtures/detail.html"
URL = "https://iaudience.kbs.co.kr/__synthetic_fixture__/input"


def manifest(tmp_path, data=None, encoding="utf-8", **extra):
    data = data if data is not None else FIXTURE.read_text().replace("—", "-").encode(encoding)
    (tmp_path / "input.html").write_bytes(data)
    body = {"synthetic": True, "sources": [{"file": "input.html", "source_url": URL,
                                            "encoding": encoding, **extra}]}
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
    return p


def test_import_is_offline_and_preserves_source_hash_and_provenance(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("import must not access network")
    monkeypatch.setattr(requests.Session, "request", forbidden)
    p = manifest(tmp_path, provenance={"saved_at": "synthetic timestamp", "method": "synthetic fixture",
                                      "policy_note": "not real source", "unexpected_headers": {"Authorization": "SECRET"}})
    report, records = import_manifest(p, fixture=True)
    event = report["events"][0]
    assert event["url"] == URL
    assert event["input_sha256"] == hashlib.sha256((tmp_path / "input.html").read_bytes()).hexdigest()
    assert all(r["input_sha256"] == event["input_sha256"] for r in records)
    assert event["inspection"]["supported_container_found"] is True
    assert report["live_html_verified"] is False
    assert "SECRET" not in json.dumps(report)
    assert all(f["status"] != "human_verified" for r in records for f in r["facts"].values())


def test_expectations_match_is_not_human_approval(tmp_path):
    parsed, _ = parse_detail(FIXTURE.read_text(), URL, "synthetic_fixture")
    fields = {key: parsed[0]["facts"][key]["value"] for key in CORE_FIELDS}
    p = manifest(tmp_path, expected_records=[{"record_index": 0, "facts": fields}])
    report, records = import_manifest(p, fixture=True)
    validation = report["events"][0]["expectations"]
    assert validation["status"] == "matched" and validation["core_field_coverage_complete"]
    assert validation["authenticity_verified"] is False
    assert records[0]["publication_ready"] is False
    assert records[0]["facts"]["name"]["status"] == "extracted_needs_review"


def test_mismatch_and_missing_record_fail_cli_and_keep_diagnostics(tmp_path):
    p = manifest(tmp_path, expected_records=[{"record_index": 9, "facts": {"name": "not present"}}])
    out = tmp_path / "run"
    assert main(["import-html", "--manifest", str(p), "--fixture", "--out", str(out)]) == 2
    report = json.loads((out / "report.json").read_text())
    assert report["status"] == "expectation_failed"
    assert report["events"][0]["expectations"]["checks"][0]["matches"] is False
    assert (out / "records.csv").exists()


def test_missing_parser_container_keeps_inspection_without_claiming_success(tmp_path):
    p = manifest(tmp_path, data=b'<html><script src="/app.js"></script><div id="root"></div></html>')
    report, records = import_manifest(p, fixture=True)
    assert records == [] and report["status"] == "unparsed"
    event = report["events"][0]
    assert event["inspection"]["script_count"] == 1
    assert event["inspection"]["dynamic_rendering_required"] == "unverified"
    assert not event["inspection"]["supported_container_found"]
    assert event["warnings"]


@pytest.mark.parametrize("encoding", ["utf-8-sig", "cp949", "euc-kr"])
def test_explicit_encoding_without_silent_guessing(tmp_path, encoding):
    p = manifest(tmp_path, encoding=encoding)
    report, records = import_manifest(p, fixture=True)
    assert records[0]["facts"]["name"]["value"] == "가상식당 알파"
    assert report["events"][0]["encoding"] == encoding


def test_wrong_encoding_returns_actionable_error(tmp_path):
    p = manifest(tmp_path, data=FIXTURE.read_text().replace("—", "-").encode("cp949"))
    with pytest.raises(ValueError, match="인코딩 불일치"):
        import_manifest(p, fixture=True)


def test_utf8_bom_manifest_supported(tmp_path):
    p = manifest(tmp_path)
    p.write_bytes(b'\xef\xbb\xbf' + p.read_bytes())
    assert import_manifest(p, fixture=True)[1]


@pytest.mark.parametrize("body", [{}, {"sources": []}, {"sources": [None]}, {"sources": [{"file": 1, "source_url": URL}]}])
def test_malformed_manifest_does_not_create_output(tmp_path, body):
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(body))
    with pytest.raises(ValueError):
        import_manifest(p, fixture=True)


def test_parent_path_and_symlink_escape_are_rejected(tmp_path):
    p = manifest(tmp_path)
    body = json.loads(p.read_text())
    body["sources"][0]["file"] = "../outside.html"
    p.write_text(json.dumps(body))
    with pytest.raises(ValueError, match="디렉터리 내부"):
        import_manifest(p, fixture=True)
    (tmp_path / "escape.html").symlink_to(tmp_path.parent / "outside.html")
    body["sources"][0]["file"] = "escape.html"
    p.write_text(json.dumps(body))
    with pytest.raises(ValueError, match="디렉터리 내부"):
        import_manifest(p, fixture=True)


def test_oversized_html_rejected(tmp_path):
    p = manifest(tmp_path, data=b"x" * 3_000_001)
    with pytest.raises(ValueError, match="3 MB"):
        import_manifest(p, fixture=True)


def test_expectation_evidence_and_unknown_fields():
    records, _ = parse_detail(FIXTURE.read_text(), URL, "synthetic_fixture")
    compare = compare_expectations(records, [{"record_index": 0, "facts": {"name": {"value": "가상식당 알파", "evidence": "WRONG"}}}])
    assert compare["status"] == "failed"
    with pytest.raises(ValueError, match="알 수 없는"):
        compare_expectations(records, [{"record_index": 0, "facts": {"invented": "x"}}])
    with pytest.raises(ValueError):
        compare_expectations(records, [{"record_index": True, "facts": {"name": "x"}}])


def test_inspection_does_not_copy_article_or_embedded_secrets():
    result = inspect_html('<article>PRIVATE_ARTICLE</article><script>PRIVATE_STATE</script><iframe src="PRIVATE_URL"></iframe>')
    text = json.dumps(result)
    assert "PRIVATE" not in text
    assert result["script_count"] == result["iframe_count"] == 1


def test_name_selector_does_not_assume_program_or_place_order():
    records, _ = parse_detail(FIXTURE.read_text(), URL, "synthetic_fixture")
    expected = [{"match": {"name": "가상식당 베타"}, "facts": {"name": "가상식당 베타", "address": "테스트시 실험로 0"}}]
    assert compare_expectations(records[::-1], expected)["status"] == "partial_match"
    assert compare_expectations([], expected)["status"] == "failed"
    assert compare_expectations([records[1], records[1]], expected)["status"] == "failed"
