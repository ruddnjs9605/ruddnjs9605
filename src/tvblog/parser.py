"""Conservative HTML adapter; unknown markup must produce a diagnostic, not a guess.

Only explicit labels are extracted. Fixtures are synthetic, NOT live KBS samples.
Live markup compatibility remains unverified until an actual page can be read.
"""
from __future__ import annotations

import re
from datetime import date
from urllib.parse import urldefrag, urljoin

from bs4 import BeautifulSoup

from .http import validate_url
from .models import FIELDS, fact, record

DATE = re.compile(r"(?<!\d)(20\d{2})\s*(?:[.\-/]|년)\s*(\d{1,2})\s*(?:[.\-/]|월)\s*(\d{1,2})(?:\s*일)?(?!\d)")
BROADCAST = re.compile(r"방송\s*(?:일자|날짜|일)\s*[:：]?\s*(.+)")
LABEL = re.compile(r"^\s*[-*▶▷○●◎•]?\s*(상호(?:명)?|식당(?:명|\s*이름)?|업체명|주소|위치|대표\s*메뉴|메뉴)\s*[:：]\s*(.+?)\s*$")
NAME_LABELS = {"상호", "상호명", "식당", "식당명", "식당이름", "업체명"}


def soup_for(html: str) -> BeautifulSoup:
    soup = BeautifulSoup(html, "html.parser")
    for el in soup(["script", "style", "nav", "header", "footer"]):
        el.decompose()
    for br in soup.find_all("br"):
        br.replace_with("\n")
    return soup


def parse_date(text: str) -> str | None:
    match = DATE.search(text)
    if not match:
        return None
    try:
        return date(*map(int, match.groups())).isoformat()
    except ValueError:
        return None


def listing_entries(html: str, url: str, today: date) -> list[dict]:
    soup = soup_for(html)
    entries, seen = [], set()
    for a in soup.select("a[href]"):
        title = a.get_text(" ", strip=True)
        # Publication dates in neighbouring cells are never treated as broadcast dates.
        if not re.search(r"방송\s*정보", title):
            continue
        if re.search(r"스페셜|재방송", title):
            continue  # A rerun listing date is not a new original broadcast.
        title_dates = {parse_date(m.group()) for m in DATE.finditer(title)}
        if None in title_dates or len(title_dates) != 1:
            continue
        broadcast_date = next(iter(title_dates))
        if not broadcast_date or date.fromisoformat(broadcast_date) > today:
            continue
        href = urldefrag(urljoin(url, a["href"]))[0]
        try:
            validate_url(href)
        except ValueError:
            continue
        if href == url or href in seen:
            continue
        seen.add(href)
        entries.append({"url": href, "broadcast_date": broadcast_date,
                        "date_evidence": title})
    return entries


def navigation_links(html: str, url: str) -> list[str]:
    result = []
    for a in soup_for(html).select("a[href]"):
        if not re.search(r"방송\s*정보", a.get_text(" ", strip=True)):
            continue
        href = urldefrag(urljoin(url, a["href"]))[0]
        try:
            validate_url(href)
        except ValueError:
            continue
        if href != url and href not in result:
            result.append(href)
    return result


def next_page(html: str, url: str) -> str | None:
    soup = soup_for(html)
    for a in soup.select("a[href]"):
        if "next" in a.get("rel", []) or a.get_text(strip=True) in ("다음", "다음 페이지"):
            target = urldefrag(urljoin(url, a["href"]))[0]
            try:
                return validate_url(target) if target != url else None
            except ValueError:
                pass
    return None


# These labels describe meaning, not the visual layout of any verified live site.
DETAIL_LABEL = re.compile(r"^\s*[-*▶▷○●◎•]?\s*(프로그램(?:명)?|방송프로그램|코너(?:명)?|방송\s*코너(?:명)?|장소\s*유형|유형|상호(?:명)?|식당(?:명|\s*이름)?|업체명|업소명|장소명|여행지명|관광지명|숙소명|주소|위치|대표\s*메뉴|소개(?:된)?\s*(?:음식|메뉴)|음식|메뉴|원(?:본)?\s*방송일|최초\s*방송일|본방송일|재방송일|방송\s*(?:일자|날짜|일)|게시일(?:자)?|등록일(?:자)?|작성일(?:자)?|재방송\s*여부)\s*[:：]\s*(.+?)\s*$")
DATE_FIELDS = {"원방송일": "original_broadcast_date", "원본방송일": "original_broadcast_date",
               "최초방송일": "original_broadcast_date", "본방송일": "original_broadcast_date",
               "재방송일": "rebroadcast_date", "방송일": "broadcast_date",
               "방송일자": "broadcast_date", "방송날짜": "broadcast_date",
               "게시일": "posted_date", "게시일자": "posted_date", "등록일": "posted_date",
               "등록일자": "posted_date", "작성일": "posted_date", "작성일자": "posted_date"}
META_LABELS = {"프로그램": "program_name", "프로그램명": "program_name", "방송프로그램": "program_name",
               "장소유형": "place_type", "유형": "place_type", "재방송여부": "is_rebroadcast"}
CORNER_LABELS = {"코너", "코너명", "방송코너", "방송코너명"}
PLACE_NAMES = NAME_LABELS | {"업소명", "장소명", "여행지명", "관광지명", "숙소명"}
TYPE_FROM_LABEL = {"식당": "식당", "식당명": "식당", "식당이름": "식당", "여행지명": "여행지",
                   "관광지명": "관광지", "숙소명": "숙소"}


def detail_lines(body) -> list[str]:
    # Preserve inline label/value spans while separating block elements and <br>.
    for row in body.select("tr"):
        cells = row.find_all(["th", "td"], recursive=False)
        if len(cells) == 2:
            label = cells[0].get_text(" ", strip=True).rstrip(" :：")
            value = cells[1].get_text(" ", strip=True)
            row.clear()
            row.append(f"{label}: {value}")
    for block in body.select("p, div, li, tr, h1, h2, h3, h4, section, dl, dt, dd"):
        block.insert_before("\n")
        block.append("\n")
    return [line.strip() for line in body.get_text("").splitlines() if line.strip()]


def labelled(line):
    match = DETAIL_LABEL.match(line)
    if match:
        label, value = match.groups()
        return re.sub(r"\s+", "", label), value
    # Date labels often omit a colon, unlike ambiguous restaurant names.
    match = re.match(r"^(원본?\s*방송일|원방송일|최초\s*방송일|본방송일|재방송일|방송\s*(?:일자|날짜|일)|게시일|등록일|작성일)\s+(.+)$", line)
    return (re.sub(r"\s+", "", match[1]), match[2]) if match else (None, None)


def unique_fact(values, url, key, warnings):
    values = [(v, e) for v, e in values if v and v != "확인 필요"]
    if len({v for v, _ in values}) > 1:
        warnings.append(f"{key} 값 충돌: 확인 필요로 저장")
        return fact()
    return fact(*values[0], url) if values else fact()


def metadata(lines, url, warnings):
    candidates = {}
    for line in lines:
        label, value = labelled(line)
        key = DATE_FIELDS.get(label) or META_LABELS.get(label)
        if key:
            if label in DATE_FIELDS:
                parsed_dates = [parse_date(m.group()) for m in DATE.finditer(value)]
                dates = set(parsed_dates)
                if None in dates or len(dates) != 1:
                    warnings.append(f"{key} 날짜 불명확: 확인 필요")
                    # An invalid/ambiguous occurrence must not be overridden by a valid one.
                    candidates.setdefault(key, []).append(("__ambiguous__", line))
                    continue
                value = next(iter(dates))
            elif key == "is_rebroadcast":
                value = {"예": "예", "아니오": "아니오", "재방송": "예", "본방송": "아니오"}.get(value)
            if value:
                candidates.setdefault(key, []).append((value, line))
        episode = re.fullmatch(r"(?:회차\s*[:：]\s*)?(\d+)\s*회", line)
        if episode:
            candidates.setdefault("episode_number", []).append((episode[1], line))
    result = {key: unique_fact(values, url, key, warnings) for key, values in candidates.items()}
    for key, values in candidates.items():
        if any(v == "__ambiguous__" for v, _ in values):
            result[key] = fact()
    return result


def resolve_dates(meta, special, url, warnings):
    """broadcast_date is the regular/original broadcast, never a special rerun date."""
    result = dict(meta)
    original = result.get("original_broadcast_date", fact())
    generic = result.get("broadcast_date", fact())
    rerun = result.get("rebroadcast_date", fact())
    state = result.get("is_rebroadcast", fact())
    if rerun["status"] != "missing":
        if state["value"] == "아니오":
            warnings.append("재방송 여부와 재방송일 충돌: 관련 날짜와 여부 확인 필요")
            for key in ("broadcast_date", "original_broadcast_date", "rebroadcast_date", "is_rebroadcast"):
                result[key] = fact()
            return result
        state = fact("예", rerun["evidence"], url)
        result["is_rebroadcast"] = state
    if special or state["value"] == "예" or rerun["status"] != "missing":
        # An unqualified date on a special can mean an airing, posting, or original date.
        result["broadcast_date"] = original
        if generic["status"] != "missing":
            warnings.append("스페셜/재방송의 일반 방송일을 원방송일 또는 재방송일로 추정하지 않음")
    elif original["status"] != "missing":
        if generic["status"] != "missing" and generic["value"] != original["value"]:
            warnings.append("방송일과 원방송일 충돌: 방송일 확인 필요")
            result["broadcast_date"] = fact()
        else:
            result["broadcast_date"] = original
    if original["status"] != "missing" and rerun["status"] != "missing" and original["value"] > rerun["value"]:
        warnings.append("원방송일이 재방송일보다 늦음: 관련 날짜 확인 필요")
        for key in ("broadcast_date", "original_broadcast_date", "rebroadcast_date"):
            result[key] = fact()
    return result


def parse_detail(html: str, url: str, source_mode: str = "live_html",
                 listing: dict | None = None) -> tuple[list[dict], list[str]]:
    soup = soup_for(html)
    body = soup.select_one(".board-view-contents, .board-view-content, .view_cont, .view-content, .bbs_view_cont, article, main")
    if body is None:
        return [], ["본문 컨테이너를 식별하지 못함: 실제 DOM에 맞는 어댑터 확인 필요"]
    # Only known program tokens in a heading can supplement an explicit program label.
    heading = body.find(["h1", "h2"]) or soup.find("title")
    heading_text = heading.get_text(" ", strip=True) if heading else ""
    heading_program = re.search(r"(?:KBS\s*)?(?:2TV\s*)?생생정보(?:\s*스페셜)?(?![가-힣A-Za-z0-9])", heading_text)
    lines = detail_lines(body)
    warnings, results = [], []
    # Page metadata precedes places/corners. Each corner has independent date context.
    sections, header, active = [], [], None
    corner = fact()
    for line in lines:
        label, value = labelled(line)
        if label in CORNER_LABELS:
            if active is not None:
                sections.append((corner, active))
            corner, active = fact(value, line, url), []
        elif label in PLACE_NAMES and active is None:
            active = [line]
        elif active is not None:
            active.append(line)
        else:
            header.append(line)
    if active is not None:
        sections.append((corner, active))
    global_meta = metadata(header, url, warnings)
    if heading_program and "program_name" not in global_meta:
        global_meta["program_name"] = fact(heading_program.group(), heading_text, url)
    special = "스페셜" in global_meta.get("program_name", fact())["value"] or "스페셜" in heading_text
    # Multiple unqualified dates on a normal page cannot identify one broadcast.
    if not special and "broadcast_date 값 충돌: 확인 필요로 저장" in warnings:
        return [], ["본문에 여러 방송일이 있어 회차를 확정할 수 없음"]
    for corner_fact, section in sections:
        # Metadata belongs to a section, never to the preceding restaurant.
        first_place = next((i for i, line in enumerate(section) if labelled(line)[0] in PLACE_NAMES), len(section))
        local_meta = metadata(section[:first_place], url, warnings)
        merged = {**global_meta, **local_meta}
        local_special = special or "스페셜" in merged.get("program_name", fact())["value"]
        meta = resolve_dates(merged, local_special, url, warnings)
        guard = local_special or meta.get("is_rebroadcast", fact())["value"] == "예"
        if listing and not guard:
            bd = meta.get("broadcast_date", fact())
            if bd["status"] != "missing" and bd["value"] != listing["broadcast_date"]:
                return [], ["목록과 본문의 방송일 불일치"]
            # Explicit conflicting/invalid metadata must not be healed from a listing.
            if "broadcast_date" not in merged:
                meta["broadcast_date"] = fact(listing["broadcast_date"], listing["date_evidence"], url)
        elif listing and guard:
            warnings.append("스페셜/재방송 목록 날짜를 원방송일로 사용하지 않음")
        current = None
        current_metadata = []

        def finish():
            if current is None:
                return
            place_meta = meta
            if current_metadata:
                raw = {**merged, **metadata(current_metadata, url, warnings)}
                place_meta = resolve_dates(raw, local_special, url, warnings)
                rerun_guard = local_special or place_meta.get("is_rebroadcast", fact())["value"] == "예"
                if listing and not rerun_guard:
                    bd = place_meta.get("broadcast_date", fact())
                    if bd["status"] != "missing" and bd["value"] != listing["broadcast_date"]:
                        warnings.append("장소별 방송일과 목록 방송일 불일치: 해당 장소 제외")
                        return
                    if "broadcast_date" not in raw:
                        place_meta["broadcast_date"] = fact(listing["broadcast_date"], listing["date_evidence"], url)
            facts = {key: fact() for key in FIELDS}
            facts.update(place_meta)
            facts["corner_name"] = corner_fact
            for key, values in current.items():
                if key == "introduced_menu":
                    # Multiple introduced dishes are a list of facts, not contradictory names.
                    values = [(" / ".join(dict.fromkeys(v for v, _ in values)),
                               " | ".join(e for _, e in values))]
                facts[key] = unique_fact(values, url, key, warnings)
            results.append(record(url, facts, source_mode))

        for line in section:
            label, value = labelled(line)
            if label in PLACE_NAMES:
                finish()
                current = {"name": [(value, line)]}
                current_metadata = []
                if label in TYPE_FROM_LABEL:
                    current["place_type"] = [(TYPE_FROM_LABEL[label], line)]
            elif current is not None:
                if label in DATE_FIELDS or label == "재방송여부":
                    current_metadata.append(line)
                elif label in ("주소", "위치"):
                    current.setdefault("address", []).append((value, line))
                elif label in ("대표메뉴", "소개음식", "소개된음식", "소개메뉴", "소개된메뉴", "음식", "메뉴"):
                    current.setdefault("introduced_menu", []).append((value, line))
                    if label == "대표메뉴":
                        current.setdefault("representative_menu", []).append((value, line))
                    elif label == "메뉴":
                        warnings.append("일반 메뉴 라벨은 대표 메뉴로 추정하지 않음")
                elif label in ("장소유형", "유형"):
                    current.setdefault("place_type", []).append((value, line))
        finish()
    if not results:
        warnings.append("명시적인 상호/식당명 라벨 없음: 임의로 상호를 추정하지 않음")
    return results, warnings
