"""Fetch a public web page or image safely and pull out article text."""

from __future__ import annotations

import ipaddress
import re
import socket
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import requests

USER_AGENT = "Mozilla/5.0 (compatible; InstaStudio/0.1)"
MAX_PAGE_BYTES = 3 * 1024 * 1024
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_REDIRECTS = 4
TIMEOUT = 10
MAX_ARTICLE_CHARS = 20000


class FetchError(Exception):
    """A URL could not be fetched or is not allowed."""


def _check_public_url(url: str) -> None:
    """Reject non-http(s) URLs and hosts that resolve to private networks (SSRF guard)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise FetchError("http 또는 https 주소만 사용할 수 있습니다.")
    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or None)
    except socket.gaierror as exc:
        raise FetchError(f"주소를 찾을 수 없습니다: {parsed.hostname}") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise FetchError("내부 네트워크 주소는 가져올 수 없습니다.")


def fetch_bytes(url: str, max_bytes: int, accept: str = "*/*") -> tuple[bytes, str, str]:
    """GET a public URL, following redirects manually so every hop is checked.

    Returns (body, content_type, final_url).
    """
    session = requests.Session()
    for _ in range(MAX_REDIRECTS + 1):
        _check_public_url(url)
        try:
            resp = session.get(
                url,
                headers={"User-Agent": USER_AGENT, "Accept": accept},
                timeout=TIMEOUT,
                allow_redirects=False,
                stream=True,
            )
        except requests.RequestException as exc:
            raise FetchError(f"가져오기 실패: {exc}") from exc
        if resp.is_redirect:
            url = urljoin(url, resp.headers.get("Location", ""))
            resp.close()
            continue
        if resp.status_code >= 400:
            resp.close()
            raise FetchError(f"사이트가 HTTP {resp.status_code}로 응답했습니다.")
        body = bytearray()
        for chunk in resp.iter_content(64 * 1024):
            body.extend(chunk)
            if len(body) > max_bytes:
                resp.close()
                raise FetchError("파일이 너무 큽니다.")
        content_type = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
        return bytes(body), content_type, url
    raise FetchError("리다이렉트가 너무 많습니다.")


class _ArticleParser(HTMLParser):
    SKIP_TAGS = {"script", "style", "noscript", "nav", "footer", "header", "aside", "form", "button"}
    BLOCK_TAGS = {"p", "h1", "h2", "h3", "li", "blockquote"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.title = ""
        self.blocks: list[tuple[bool, str]] = []  # (inside <article>, text)
        self._skip = 0
        self._article = 0
        self._in_title = False
        self._buf: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "meta":
            key = (a.get("property") or a.get("name") or "").lower()
            if key and a.get("content"):
                self.meta.setdefault(key, a["content"].strip())
        elif tag == "title":
            self._in_title = True
        elif tag in self.SKIP_TAGS:
            self._skip += 1
        elif tag == "article":
            self._article += 1
        elif tag in self.BLOCK_TAGS and not self._skip:
            self._flush()
            self._buf = []
        elif tag == "br" and self._buf is not None:
            self._buf.append(" ")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag in self.SKIP_TAGS and self._skip:
            self._skip -= 1
        elif tag == "article" and self._article:
            self._flush()
            self._article -= 1
        elif tag in self.BLOCK_TAGS:
            self._flush()

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif self._buf is not None and not self._skip:
            self._buf.append(data)

    def _flush(self):
        if self._buf is not None:
            text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            if len(text) >= 20:
                self.blocks.append((self._article > 0, text))
            self._buf = None


@dataclass
class Article:
    url: str
    title: str
    text: str
    site_name: str = ""
    image_url: str = ""
    description: str = ""
    warnings: list[str] = field(default_factory=list)


def parse_article(html: str, url: str) -> Article:
    parser = _ArticleParser()
    parser.feed(html)
    parser.close()
    parser._flush()

    in_article = [t for inside, t in parser.blocks if inside]
    texts = in_article if sum(map(len, in_article)) >= 300 else [t for _, t in parser.blocks]
    seen: set[str] = set()
    unique = [t for t in texts if not (t in seen or seen.add(t))]
    text = "\n".join(unique)[:MAX_ARTICLE_CHARS]

    meta = parser.meta
    image = meta.get("og:image") or meta.get("twitter:image") or ""
    article = Article(
        url=url,
        title=(meta.get("og:title") or parser.title).strip(),
        text=text,
        site_name=meta.get("og:site_name", ""),
        image_url=urljoin(url, image) if image else "",
        description=meta.get("og:description") or meta.get("description") or "",
    )
    if len(text) < 200:
        article.warnings.append("본문을 충분히 추출하지 못했습니다. 기사 내용을 직접 붙여넣어 주세요.")
    return article


def fetch_article(url: str) -> Article:
    body, content_type, final_url = fetch_bytes(url, MAX_PAGE_BYTES, "text/html,*/*;q=0.8")
    if content_type and "html" not in content_type:
        raise FetchError("웹 페이지(HTML)가 아닙니다.")
    match = re.search(rb'charset=["\']?([\w-]+)', body[:4096], re.I)
    encoding = match.group(1).decode() if match else "utf-8"
    try:
        html = body.decode(encoding, errors="replace")
    except LookupError:
        html = body.decode("utf-8", errors="replace")
    return parse_article(html, final_url)


def fetch_image(url: str) -> tuple[bytes, str]:
    body, content_type, _ = fetch_bytes(url, MAX_IMAGE_BYTES, "image/*")
    if not content_type.startswith("image/"):
        raise FetchError("이미지 파일이 아닙니다.")
    return body, content_type
