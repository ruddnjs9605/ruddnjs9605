from __future__ import annotations

import hashlib
from datetime import datetime, timezone

UNKNOWN = "확인 필요"
FIELDS = ("name", "address", "representative_menu", "broadcast_date", "episode_number",
          "program_name", "posted_date", "corner_name", "place_type", "introduced_menu",
          "original_broadcast_date", "rebroadcast_date", "is_rebroadcast")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fact(value: str | None = None, evidence: str = "", source_url: str = "") -> dict:
    if value and value.strip() in (UNKNOWN, "미상", "정보 없음", "미확인"):
        value = None
    return {"value": value or UNKNOWN,
            "status": "extracted_needs_review" if value else "missing",
            "evidence": evidence, "source_url": source_url if value else ""}


def record(source_url: str, facts: dict, source_mode: str) -> dict:
    identity = source_url + "\n" + facts["name"]["value"] + "\n" + facts["address"]["value"] + "\n" + facts["broadcast_date"]["value"]
    identity += "\n" + facts["corner_name"]["value"] + "\n" + facts["original_broadcast_date"]["value"]
    categories = {"식당": "restaurant", "음식점": "restaurant", "여행지": "travel_site",
                  "관광지": "travel_site", "숙소": "accommodation", "숙박시설": "accommodation", "카페": "cafe"}
    return {"schema_version": 2, "id": hashlib.sha256(identity.encode()).hexdigest()[:20],
            "program": facts["program_name"]["value"],
            "category": categories.get(facts["place_type"]["value"], UNKNOWN),
            "facts": facts, "official_source_url": source_url,
            "additional_sources": [], "collected_at": now(),
            "source_mode": source_mode, "independent_confirmation": UNKNOWN,
            "publication_ready": False}
