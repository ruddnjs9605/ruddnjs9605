from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from .http import AccessError, Client
from .models import now
from .parser import listing_entries, navigation_links, next_page, parse_detail

IAUDIENCE_URLS = (
    "https://iaudience.kbs.co.kr/broadcast/",
    "https://iaudience.kbs.co.kr/broadcast/11344",
    "https://iaudience.kbs.co.kr/broadcast/11279",
    "https://iaudience.kbs.co.kr/broadcast/11234",
)

PROGRAM_URL = "https://program.kbs.co.kr/2tv/culture/reallive/pc/index.html"
TARGETS = [
    ("프로그램 홈 후보(현재 URL 미검증)", PROGRAM_URL),
    ("공식 편성표 진입점 후보", "https://schedule.kbs.co.kr/"),
    ("KBS 공식 홈페이지", "https://www.kbs.co.kr/"),
    ("공식 게시판 호스트 후보(API 계약 미검증)", "https://pbbs.kbs.co.kr/"),
    ("API 호스트 후보(공개 API 제공 여부 미확인)", "https://apis.kbs.co.kr/"),
]


def base_report(mode: str, count: int) -> dict:
    return {"schema_version": 1, "started_at": now(), "mode": mode,
            "program": "KBS 2TV 생생정보", "requested_episode_count": count,
            "selected_episode_count": 0, "successful_episode_count": 0,
            "record_count": 0, "latest_five_verified": False, "events": [],
            "limitations": ["실제 KBS DOM 적합성은 라이브 본문 수집 후 검증 필요",
                            "방송일은 게시일/요일로 추정하지 않음",
                            "추출 필드는 사람 대조 전 검증된 정보로 취급하지 않음"]}


def error_event(exc: AccessError, stage: str) -> dict:
    return {"stage": stage, "url": exc.url, "outcome": exc.kind, "detail": exc.detail}


def probe(client: Client) -> dict:
    report = base_report("live_probe", 5)
    for label, url in TARGETS:
        try:
            html = client.get_html(url)
            report["events"].append({"label": label, "url": url, "outcome": "html_accessible",
                                     "broadcast_info_links": navigation_links(html, url)})
        except AccessError as exc:
            report["events"].append({"label": label, **error_event(exc, "policy_and_access")})
    # New source: inspect robots only. No API/terms permission is established.
    policy_failure = None
    for url in IAUDIENCE_URLS:
        try:
            if policy_failure is not None:
                raise policy_failure
            client.check_policy(url)
            event = {"outcome": "robots_allows_path", "stage": "robots"}
        except AccessError as exc:
            if exc.kind != "robots_disallowed":
                policy_failure = exc
            event = error_event(exc, "robots")
        report["events"].append({**event, "candidate_url": url,
                                 "content_requested": False, "terms_permission": "unverified",
                                 "api_contract": "unverified"})
    report.update(status="access_checked_not_collected", audit=client.audit, finished_at=now())
    return report


def collect(client: Client, listing_url: str | None, count: int = 5,
            today: date | None = None) -> tuple[dict, list[dict]]:
    today = today or datetime.now(ZoneInfo("Asia/Seoul")).date()
    report, records = base_report("live_collect", count), []
    report["as_of_kst"] = today.isoformat()
    try:
        if listing_url:
            url, html = listing_url, client.get_html(listing_url)
        else:
            html = client.get_html(PROGRAM_URL)
            links = navigation_links(html, PROGRAM_URL)
            if len(links) != 1:
                report.update(status="needs_listing_url")
                report["events"].append({"stage": "discovery", "outcome": "ambiguous_or_dynamic",
                                         "candidate_urls": links,
                                         "detail": "방송정보 목록 링크를 하나로 식별하지 못함. 공식 페이지 확인 후 --listing-url 지정"})
                return report, records
            url = links[0]
            html = client.get_html(url)
        report["listing_url"] = url
        entries, visited = [], set()
        for _ in range(3):
            if url in visited:
                break
            visited.add(url)
            entries.extend(listing_entries(html, url, today))
            if len({e["broadcast_date"] for e in entries}) >= count:
                break
            target = next_page(html, url)
            if not target:
                break
            url, html = target, client.get_html(target)
        # Multiple posts for one day count as one episode date, not separate broadcasts.
        unique = {e["url"]: e for e in entries}
        dates = sorted({e["broadcast_date"] for e in unique.values()}, reverse=True)[:count]
        selected = [e for e in unique.values() if e["broadcast_date"] in dates]
        report["selected_episode_count"] = len(dates)
        report["selection_scope"] = "공식 목록 최대 3페이지에서 제목에 전체 방송 날짜가 명시된 게시물; 최신성은 추가 확인 필요"
        successful = set()
        failed_dates = set()
        for entry in sorted(selected, key=lambda e: e["broadcast_date"], reverse=True):
            try:
                detail = client.get_html(entry["url"])
                parsed, warnings = parse_detail(detail, entry["url"], listing=entry)
                records.extend(parsed)
                if any(r["facts"].get("is_rebroadcast", {}).get("value") == "예"
                       or "스페셜" in r.get("program", "") for r in parsed):
                    failed_dates.add(entry["broadcast_date"])
                    warnings.append("스페셜/재방송을 원방송 회차 성공 수에서 제외")
                elif parsed:
                    successful.add(entry["broadcast_date"])
                else:
                    failed_dates.add(entry["broadcast_date"])
                report["events"].append({**entry, "outcome": "parsed" if parsed else "unsupported_or_empty",
                                         "records": len(parsed), "warnings": warnings})
            except AccessError as exc:
                failed_dates.add(entry["broadcast_date"])
                report["events"].append(error_event(exc, "detail"))
        report["successful_episode_count"] = len(successful - failed_dates)
        report["status"] = "collected_needs_review" if len(successful - failed_dates) == count else "incomplete"
        if not entries:
            report["events"].append({"stage": "listing", "outcome": "unsupported_or_empty",
                                     "detail": "명시된 날짜+방송정보 HTML 링크 없음. 동적 API/DOM 조사가 필요하며 엔드포인트를 추측하지 않음"})
    except AccessError as exc:
        report["status"] = "blocked"
        report["events"].append(error_event(exc, "discovery_or_listing"))
    finally:
        # IDs are source + name + address; repeated listing links do not duplicate data.
        records[:] = list({r["id"]: r for r in records}.values())
        report.update(record_count=len(records), audit=client.audit, finished_at=now())
    return report, records
