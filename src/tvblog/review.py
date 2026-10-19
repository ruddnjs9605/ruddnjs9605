"""Explicit human comparison of extracted facts; never automatic verification."""
from copy import deepcopy
from urllib.parse import urlsplit

from .models import FIELDS, now


def apply_review(records: list[dict], decisions: dict) -> list[dict]:
    if not decisions.get("reviewer", "").strip():
        raise ValueError("reviewer 필수: 실제 원문 대조를 완료한 사람만 승인하세요")
    result = deepcopy(records)
    by_id = {item["id"]: item for item in result}
    for decision in decisions.get("records", []):
        item = by_id[decision["id"]]
        for key, approval in decision.get("fields", {}).items():
            if key not in FIELDS:
                raise ValueError("알 수 없는 필드")
            field = item["facts"][key]
            if field["status"] == "missing" or not field["evidence"] or not field["source_url"]:
                raise ValueError("출처/근거가 없는 값은 승인할 수 없음")
            if approval.get("expected_value") != field["value"] or approval.get("evidence") != field["evidence"]:
                raise ValueError("승인 값/근거가 추출 결과와 다름; 오래된 검토일 수 있음")
            if not approval.get("note", "").strip():
                raise ValueError("원문 대조 내용 note 필수")
            field.update(status="human_verified", reviewed_by=decisions["reviewer"],
                         reviewed_at=now(), review_note=approval["note"])
        for source in decision.get("additional_sources", []):
            if any(ord(c) < 33 for c in source["url"]) or any(c in source["url"] for c in "<>\\"):
                raise ValueError("추가 출처 URL의 비정상 문자")
            p = urlsplit(source["url"])
            if p.scheme != "https" or not p.hostname or p.username or p.password:
                raise ValueError("추가 출처는 인증정보 없는 HTTPS URL이어야 함")
            if not source.get("note", "").strip():
                raise ValueError("추가 출처에서 확인한 내용 note 필수")
            fields = source.get("fields", [])
            if not fields or any(f not in FIELDS or item["facts"][f]["status"] != "human_verified" for f in fields):
                raise ValueError("추가 출처가 대조한 승인 필드 fields 필수")
            item["additional_sources"].append({**source, "status": "human_confirmed",
                                              "reviewed_by": decisions["reviewer"], "reviewed_at": now()})
        item["independent_confirmation"] = "partial_human_confirmation" if item["additional_sources"] else "확인 필요"
        # Never auto-authorize publication, even when all fields are reviewed.
        item["publication_ready"] = False
    return result
