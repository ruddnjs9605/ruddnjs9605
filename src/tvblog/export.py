from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from .models import FIELDS, UNKNOWN, fact


def write_json(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def safe_cell(value) -> str:
    text = str(value)
    # Spreadsheet formula injection, including whitespace-prefixed formulas.
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text


def markdown(text: str) -> str:
    text = text.replace("\n", " ").replace("\r", " ")
    return re.sub(r"([\\`*_{}\[\]()<>#!|])", r"\\\1", text)


def render_draft(item: dict) -> str:
    def value(key):
        f = item["facts"].get(key, fact())
        return markdown(f["value"]) if f["status"] == "human_verified" else UNKNOWN
    title = value("name")
    if title == UNKNOWN:
        title = "장소 정보 확인용"
    lines = [f"# 생생정보 {title} — 네이버 블로그 초안", "",
             "> 게시 전 검토용입니다. 원문과 대조한 필드만 반영합니다.", "",
             f"- 방송: {value('program_name')}",
             f"- 원방송 기준 방송일: {value('broadcast_date')}",
             f"- 명시된 원방송일: {value('original_broadcast_date')}",
             f"- 재방송일: {value('rebroadcast_date')}",
             f"- 재방송 여부: {value('is_rebroadcast')}",
             f"- 방송정보 게시일: {value('posted_date')}",
             f"- 코너: {value('corner_name')}",
             f"- 장소 유형: {value('place_type')}",
             f"- 회차: {value('episode_number')}",
             f"- 식당 이름: {value('name')}",
             f"- 주소: {value('address')}",
             f"- 소개 음식/메뉴: {value('introduced_menu')}",
             f"- 대표 메뉴: {value('representative_menu')}", "",
             "방문 전 영업 여부, 영업시간, 가격, 예약 방법은 업장에 직접 확인해주세요.",
             "직접 방문한 후기나 맛 평가는 포함하지 않았습니다.", "", "## 출처", "",
             f"- 공식 방송정보 원문: <{item['official_source_url']}>"]
    for source in item["additional_sources"]:
        lines.append(f"- 사람이 추가 확인한 출처: <{source['url']}>")
    if not item["additional_sources"]:
        lines.append("- 추가 출처: 확인 필요")
    lines += ["", "## 게시 전 확인", "",
              "- 확인 필요 항목을 원문/업장 공식 안내와 대조해주세요.",
              "- 방송 화면·사진·원문 전문은 포함하지 않았습니다. 별도 이용 허락을 확인해주세요.", ""]
    if item["source_mode"] == "synthetic_fixture":
        lines.insert(0, "> 합성 테스트 자료입니다. 실제 방송·업체 정보가 아니며 게시하면 안 됩니다.\n")
    return "\n".join(lines)


def export_run(out: Path, report: dict, records: list[dict]):
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / "report.json", report)
    write_json(out / "records.json", records)
    from .candidates import generate_candidates
    write_json(out / "candidates.json", generate_candidates(records))
    columns = ["id", "program", "category", "official_source_url", "source_mode",
               "collected_at", "independent_confirmation", "publication_ready", "additional_sources"]
    columns += [f"{field}_{suffix}" for field in FIELDS
                for suffix in ("value", "status", "evidence", "source_url")]
    with (out / "records.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for item in records:
            row = {key: item[key] for key in columns if key in item}
            row["additional_sources"] = json.dumps(item["additional_sources"], ensure_ascii=False)
            for field in FIELDS:
                for suffix in ("value", "status", "evidence", "source_url"):
                    row[f"{field}_{suffix}"] = item["facts"].get(field, fact())[suffix]
            writer.writerow({key: safe_cell(val) for key, val in row.items()})
    drafts = out / "drafts"
    drafts.mkdir()
    for item in records:
        (drafts / f"{item['id']}.md").write_text(render_draft(item), encoding="utf-8")
