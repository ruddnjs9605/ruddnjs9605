"""Rate-limited HTTPS client. Policy failures are closed, never bypassed."""
from __future__ import annotations

import time
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import requests

HOSTS = frozenset({"www.kbs.co.kr", "program.kbs.co.kr", "schedule.kbs.co.kr",
                   "pbbs.kbs.co.kr", "apis.kbs.co.kr", "iaudience.kbs.co.kr"})
USER_AGENT = "TVBlogResearch/0.1"


class AccessError(RuntimeError):
    def __init__(self, kind: str, url: str, detail: str):
        self.kind, self.url, self.detail = kind, url, detail
        super().__init__(f"{kind}: {detail}")


def validate_url(url: str) -> str:
    if any(ord(c) < 33 for c in url) or any(c in url for c in "<>\\"):
        raise ValueError("URL에 공백/제어문자/비정상 구분자를 사용할 수 없습니다")
    p = urlsplit(url)
    if (p.scheme != "https" or p.hostname not in HOSTS or p.username or p.password
            or p.port not in (None, 443)):
        raise ValueError("허용된 KBS 호스트의 HTTPS URL만 사용할 수 있습니다")
    return url


class Client:
    def __init__(self, delay: float = 2.0, session=None, sleeper=time.sleep,
                 clock=time.monotonic):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.delay = max(2.0, delay)
        self.sleeper, self.clock = sleeper, clock
        self.last: float | None = None
        self.policies: dict[str, RobotFileParser] = {}
        self.audit: list[dict] = []

    def _request(self, url: str, redirects: int = 0, robots: bool = False):
        validate_url(url)
        if redirects > 3:
            raise AccessError("redirect_limit", url, "리디렉션 제한")
        if self.last is not None:
            self.sleeper(max(0, self.delay - (self.clock() - self.last)))
        self.last = self.clock()
        try:
            response = self.session.get(url, timeout=(10, 25), allow_redirects=False,
                                        stream=True)
        except requests.RequestException as exc:
            # Do not serialize proxy URLs or authentication from exception messages.
            kind = "proxy_error" if isinstance(exc, requests.exceptions.ProxyError) else "network_error"
            self.audit.append({"url": url, "outcome": kind,
                               "error_type": type(exc).__name__})
            raise AccessError(kind, url, type(exc).__name__) from exc
        self.audit.append({"url": url, "status": response.status_code})
        try:
            if response.is_redirect:
                target = urljoin(url, response.headers.get("Location", ""))
                validate_url(target)
                # Every content redirect is checked against the destination policy.
                if not robots:
                    self.check_policy(target)
                return self._request(target, redirects + 1, robots=robots)
            chunks, size = [], 0
            for chunk in response.iter_content(chunk_size=65536):
                size += len(chunk)
                if size > 3_000_000:
                    raise AccessError("size_limit", url, "3 MB 응답 제한")
                chunks.append(chunk)
            response._content = b"".join(chunks)
            response._content_consumed = True
            return response
        finally:
            response.close()

    def check_policy(self, url: str):
        validate_url(url)
        p = urlsplit(url)
        origin = f"{p.scheme}://{p.netloc}"
        if origin not in self.policies:
            robots_url = origin + "/robots.txt"
            r = self._request(robots_url, robots=True)
            policy = RobotFileParser(robots_url)
            if r.status_code in (404, 410):
                policy.parse([])  # No robots file; does not grant copyright permission.
            elif r.status_code == 200:
                if "<html" in r.text.lower() or "<!doctype html" in r.text.lower():
                    raise AccessError("robots_unreadable", robots_url, "robots 대신 HTML 응답")
                policy.parse(r.text.splitlines())
            else:
                raise AccessError("robots_unavailable", robots_url,
                                  f"HTTP {r.status_code}; 정책 확인 전 수집 중단")
            self.policies[origin] = policy
        policy = self.policies[origin]
        if not policy.can_fetch(USER_AGENT, url):
            raise AccessError("robots_disallowed", url, "robots.txt 수집 금지")
        self.delay = max(self.delay, policy.crawl_delay(USER_AGENT) or 0)
        rate = policy.request_rate(USER_AGENT)
        if rate and rate.requests:
            self.delay = max(self.delay, rate.seconds / rate.requests)

    def get_html(self, url: str) -> str:
        self.check_policy(url)
        if urlsplit(url).hostname == "iaudience.kbs.co.kr":
            raise AccessError("policy_review_required", url,
                              "신규 소스의 API/이용 허락 미확인: 라이브 본문 수집 비활성, 허용된 저장 HTML import 사용")
        r = self._request(url)
        if r.status_code != 200:
            raise AccessError("http_error", url, f"HTTP {r.status_code}; 재시도/우회하지 않음")
        if not any(t in r.headers.get("Content-Type", "").lower()
                   for t in ("text/html", "application/xhtml+xml")):
            raise AccessError("unsupported_content", url, "HTML 응답이 아님")
        # requests defaults text/* to Latin-1 even on Korean sites without charset.
        if not r.encoding or r.encoding.lower() == "iso-8859-1":
            r.encoding = r.apparent_encoding or "utf-8"
        return r.text
