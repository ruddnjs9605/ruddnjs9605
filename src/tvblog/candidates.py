"""Rule-based editorial suggestions from evidence-bearing records, never search metrics."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from .models import FIELDS, UNKNOWN, fact

# Optional future adapter fields are handled as missing on legacy records.
EDITORIAL_FIELDS = (*FIELDS, "broadcast_kind", "scheduled_date", "scheduled_time", "price", "opening_hours")
REQUIRED_DRAFT_FIELDS = ("program_name", "name", "address", "broadcast_date")


def usable(field: dict) -> bool:
    return (field.get("status") in ("extracted_needs_review", "human_verified")
            and field.get("value") not in (None, "", UNKNOWN)
            and bool(field.get("evidence")) and bool(field.get("source_url")))


def generate_candidates(records: list[dict]) -> list[dict]:
    candidates, seen = [], set()
    for record in records:
        fields = {key: record.get("facts", {}).get(key, fact()) for key in EDITORIAL_FIELDS}
        if not usable(fields["name"]):
            continue
        source = record.get("official_source_url")
        if not source or source != fields["name"]["source_url"]:
            continue
        identity = record["id"]
        if identity in seen:
            continue
        seen.add(identity)
        program = fields["program_name"]["value"] if usable(fields["program_name"]) else "방송 소개"
        name = fields["name"]["value"]
        suffix = "위치와 방송정보" if usable(fields["address"]) else "방송정보 정리"
        confirmed = {key: f for key, f in fields.items() if usable(f) and f["status"] == "human_verified"}
        unreviewed = {key: f for key, f in fields.items() if usable(f) and f["status"] != "human_verified"}
        unknown = [key for key, f in fields.items() if not usable(f)]
        synthetic = record.get("source_mode") == "synthetic_fixture"
        ready = not synthetic and all(key in confirmed for key in REQUIRED_DRAFT_FIELDS)
        # Scheduling and original dates stay separate: no date is synthesized for specials.
        candidates.append({
            "id": f"{identity}-location", "record_id": identity,
            "recommended_title": f"{program} {name} {suffix}",
            "title_status": "human_verified_inputs" if ready else "needs_review",
            "target_program": fields["program_name"], "target_corner": fields["corner_name"],
            "broadcast_date": fields["broadcast_date"],
            "original_broadcast_date": fields["original_broadcast_date"],
            "scheduled_date": fields["scheduled_date"], "scheduled_time": fields["scheduled_time"],
            "related_places": [{"name": fields["name"], "address": fields["address"],
                                "place_type": fields["place_type"]}],
            "confirmed_facts": confirmed, "unreviewed_extractions": unreviewed,
            "unknown_information": unknown, "official_sources": [source],
            "suggested_search_keywords": [f"{program} {name}", f"{name} 위치"],
            "keyword_status": "예상 검색 키워드", "search_volume": UNKNOWN,
            "popularity": UNKNOWN, "draft_generation_possible": ready,
            "readiness_note": "프로그램명·장소명·주소·원방송 기준 방송일의 사람 승인 필요; 게시/재이용 허락과 별개",
            "source_mode": record.get("source_mode", UNKNOWN),
            "synthetic": synthetic, "publication_ready": False,
        })
    return candidates


def export_candidates(out: Path, report: dict, candidates: list[dict]):
    # Local import avoids a cycle when export_run also adds candidate output.
    from .export import safe_cell, write_json
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / "report.json", report)
    write_json(out / "candidates.json", candidates)
    columns = ("id", "recommended_title", "title_status", "keyword_status", "broadcast_date",
               "official_sources", "unknown_information", "draft_generation_possible", "synthetic")
    with (out / "candidates.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for item in candidates:
            writer.writerow({key: safe_cell(json.dumps(item[key], ensure_ascii=False)
                                           if isinstance(item[key], (dict, list)) else item[key])
                             for key in columns})
