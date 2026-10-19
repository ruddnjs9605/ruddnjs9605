"""Offline inspection and parsing of permitted, user-provided official HTML.

Never accesses the network, executes scripts, or promotes extracted facts to verified.
An expected-value match checks a supplied test specification, not source authenticity.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from bs4 import BeautifulSoup

from .collector import base_report
from .http import validate_url
from .models import FIELDS, now
from .parser import DETAIL_LABEL, parse_detail

MAX_HTML_BYTES = 3_000_000
BODY_SELECTORS = (".board-view-contents", ".board-view-content", ".view_cont",
                  ".view-content", ".bbs_view_cont", "article", "main")
ENCODINGS = {"utf-8", "utf-8-sig", "cp949", "euc-kr"}
CORE_FIELDS = {"program_name", "broadcast_date", "posted_date", "corner_name",
               "place_type", "name", "introduced_menu", "address"}


def inspect_html(html: str) -> dict:
    """Only structural counts; no copied article, embedded state, assets, or scripts."""
    soup = BeautifulSoup(html, "html.parser")
    script_count = len(soup.find_all("script"))
    iframe_count = len(soup.find_all("iframe"))
    containers = {selector: len(soup.select(selector)) for selector in BODY_SELECTORS}
    detail_links = sum(1 for a in soup.select("a[href]")
                       if "/broadcast/" in a.get("href", ""))
    for node in soup(["script", "style", "nav", "header", "footer"]):
        node.decompose()
    text = soup.get_text("\n", strip=True)
    return {"candidate_container_counts": containers,
            "heading_count": len(soup.select("h1,h2,h3,h4")),
            "table_row_count": len(soup.select("tr")), "script_count": script_count,
            "iframe_count": iframe_count, "broadcast_href_count": detail_links,
            "visible_text_characters": len(text),
            "labelled_line_count": sum(bool(DETAIL_LABEL.match(line)) for line in text.splitlines()),
            "supported_container_found": any(containers.values()),
            "dynamic_rendering_required": "unverified",
            "notes": ["script presence alone does not prove JavaScript rendering is required",
                      "No assets, iframe URLs or linked pages are fetched"]}


def compare_expectations(records: list[dict], expectations) -> dict:
    if expectations is None:
        return {"status": "not_requested", "checks": [], "authenticity_verified": False}
    if not isinstance(expectations, list) or not expectations:
        raise ValueError("expected_records는 비어 있지 않은 배열이어야 합니다")
    checks, complete = [], True
    for spec in expectations:
        if not isinstance(spec, dict):
            raise ValueError("expected_records 항목은 객체여야 합니다")
        index, fields = spec.get("record_index"), spec.get("facts")
        selector = spec.get("match")
        if not isinstance(fields, dict) or not fields:
            raise ValueError("기대값에는 비어 있지 않은 facts가 필요합니다")
        if selector is not None:
            if ("record_index" in spec or not isinstance(selector, dict) or not selector
                    or set(selector) - set(FIELDS) or any(not isinstance(v, str) for v in selector.values())):
                raise ValueError("match는 알려진 필드의 문자열 매핑이며 record_index와 함께 쓸 수 없습니다")
            matching = [i for i, r in enumerate(records)
                        if all(r["facts"].get(k, {}).get("value") == v for k, v in selector.items())]
            index = matching[0] if len(matching) == 1 else None
        elif type(index) is not int or index < 0:
            raise ValueError("0 이상의 record_index 또는 유일한 장소를 고르는 match가 필요합니다")
        if set(fields) - set(FIELDS):
            raise ValueError("기대값에 알 수 없는 facts 필드가 있습니다")
        complete = complete and CORE_FIELDS.issubset(fields)
        for key, expected in fields.items():
            if isinstance(expected, str):
                expected = {"value": expected}
            if (not isinstance(expected, dict) or not isinstance(expected.get("value"), str)
                    or ("evidence" in expected and not isinstance(expected["evidence"], str))):
                raise ValueError("기대 필드는 문자열 또는 value/evidence 문자열 객체여야 합니다")
            actual = records[index]["facts"].get(key) if index is not None and index < len(records) else None
            checks.append({"record_index": index, "selector": selector, "field": key, "expected": expected,
                           "actual": actual,
                           "matches": actual is not None and all(actual.get(k) == v for k, v in expected.items())})
    passed = all(c["matches"] for c in checks)
    return {"status": ("matched" if complete else "partial_match") if passed else "failed",
            "core_field_coverage_complete": complete, "checks": checks,
            "authenticity_verified": False,
            "note": "제공한 기대값과의 비교입니다. 실제 사이트·허락·원문 진위 검증 또는 사용자 승인을 대신하지 않습니다."}


def import_manifest(manifest_path: Path, fixture: bool = False) -> tuple[dict, list[dict]]:
    manifest_path = manifest_path.resolve()
    with manifest_path.open("rb") as stream:
        raw = stream.read(1_000_001)
    if len(raw) > 1_000_000:
        raise ValueError("manifest 크기 제한 1 MB")
    manifest = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(manifest, dict) or not isinstance(manifest.get("sources"), list) or not manifest["sources"]:
        raise ValueError("manifest에는 비어 있지 않은 sources 배열이 필요합니다")
    if manifest.get("synthetic") and not fixture:
        raise ValueError("합성 manifest는 --fixture로만 처리 가능")
    report = base_report("synthetic_fixture" if fixture else "provided_html", 0)
    report.update(live_html_verified=False, source_authenticity="unverified", input_file_count=0)
    records = []
    validation_failed = False
    for source in manifest["sources"]:
        if not isinstance(source, dict) or not isinstance(source.get("file"), str) or not isinstance(source.get("source_url"), str):
            raise ValueError("각 source에는 file과 source_url 문자열이 필요합니다")
        url = validate_url(source["source_url"])
        if "__synthetic_fixture__" in url and not fixture:
            raise ValueError("합성 URL은 --fixture로만 처리 가능")
        path = (manifest_path.parent / source["file"]).resolve()
        if not path.is_relative_to(manifest_path.parent):
            raise ValueError("HTML 파일은 manifest 디렉터리 내부에 있어야 함")
        encoding = source.get("encoding", "utf-8-sig")
        if not isinstance(encoding, str) or encoding not in ENCODINGS:
            raise ValueError("encoding은 utf-8, utf-8-sig, cp949, euc-kr 중 하나여야 합니다")
        with path.open("rb") as stream:
            data = stream.read(MAX_HTML_BYTES + 1)
        if len(data) > MAX_HTML_BYTES:
            raise ValueError("HTML 파일 크기 제한 3 MB")
        try:
            html = data.decode(encoding)
        except UnicodeDecodeError as exc:
            raise ValueError(f"HTML 인코딩 불일치: {source['file']}; 올바른 encoding을 manifest에 지정하세요") from exc
        inspection = inspect_html(html)
        parsed, warnings = parse_detail(html, url, report["mode"])
        comparison = compare_expectations(parsed, source.get("expected_records"))
        validation_failed = validation_failed or comparison["status"] == "failed"
        provenance = source.get("provenance", {})
        if not isinstance(provenance, dict):
            raise ValueError("provenance는 객체여야 합니다")
        provenance = {key: value for key, value in provenance.items()
                      if key in ("saved_at", "method", "policy_note", "policy_url")}
        if any(not isinstance(v, str) for v in provenance.values()):
            raise ValueError("provenance 값은 문자열이어야 합니다")
        if provenance.get("policy_url"):
            validate_url(provenance["policy_url"])
        digest = hashlib.sha256(data).hexdigest()
        for item in parsed:
            item["input_sha256"] = digest
        records.extend(parsed)
        report["input_file_count"] += 1
        report["events"].append({"url": url, "file": source["file"], "encoding": encoding,
                                 "input_bytes": len(data), "input_sha256": digest,
                                 "provenance": provenance, "provenance_verification": "user_declared_unverified",
                                 "records": len(parsed), "warnings": warnings,
                                 "inspection": inspection, "expectations": comparison})
    records = list({r["id"]: r for r in records}.values())
    status = "expectation_failed" if validation_failed else "imported_needs_review" if records else "unparsed"
    report.update(status=status, record_count=len(records), finished_at=now())
    report["limitations"].extend(["사용자 제공 HTML의 진위/최신성 및 원격 접근·수집 허용 여부는 확인하지 않음",
                                  "DOM 통계나 기대값 일치가 실제 KBS 파서 검증 성공을 뜻하지 않음"])
    return report, records
