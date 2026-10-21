import socket

import pytest

from insta_studio import fetcher

HTML = """<html><head>
<title>Fallback title</title>
<meta property="og:title" content="허미미, 나고야서 금메달">
<meta property="og:site_name" content="테스트뉴스">
<meta property="og:image" content="/img/judo.jpg">
<script>var junk = "이건 본문이 아닙니다 이건 본문이 아닙니다";</script>
</head><body>
<nav><p>메뉴 메뉴 메뉴 메뉴 메뉴 메뉴 메뉴 메뉴</p></nav>
<article>
<h1>허미미, 나고야서 금메달</h1>
<p>지난 대회 은메달의 아쉬움을 딛고 허미미가 결승에서 승리했다. """ + "경기 내용 " * 40 + """</p>
<p>할머니와의 약속을 지켰다며 소감을 밝혔다. 할머니와의 약속을 지켰다며 소감을 밝혔다.</p>
</article>
<footer><p>Copyright 테스트뉴스 all rights reserved 무단 전재 금지</p></footer>
</body></html>"""


def test_parse_article_prefers_article_and_meta():
    a = fetcher.parse_article(HTML, "https://news.example.com/a/1")
    assert a.title == "허미미, 나고야서 금메달"
    assert a.site_name == "테스트뉴스"
    assert a.image_url == "https://news.example.com/img/judo.jpg"
    assert "은메달의 아쉬움" in a.text
    assert "할머니와의 약속" in a.text
    assert "메뉴" not in a.text
    assert "junk" not in a.text
    assert "Copyright" not in a.text
    assert a.warnings == []


def test_parse_article_warns_when_text_short():
    a = fetcher.parse_article("<html><body><p>짧음</p></body></html>", "https://x.example.com")
    assert a.text == ""
    assert a.warnings


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://example.com/x", "http://"])
def test_rejects_non_http_urls(url):
    with pytest.raises(fetcher.FetchError):
        fetcher._check_public_url(url)


@pytest.mark.parametrize("ip", ["127.0.0.1", "10.0.0.5", "192.168.1.1", "169.254.169.254", "::1"])
def test_rejects_private_addresses(monkeypatch, ip):
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(family, 1, 6, "", (ip, 80))])
    with pytest.raises(fetcher.FetchError):
        fetcher._check_public_url("http://evil.example.com/")


def test_accepts_public_address(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(socket.AF_INET, 1, 6, "", ("93.184.216.34", 80))])
    fetcher._check_public_url("https://example.com/")
