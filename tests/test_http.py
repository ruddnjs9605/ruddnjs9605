import requests
import pytest

from tvblog.http import AccessError, Client, validate_url

URL = "https://program.kbs.co.kr/test"


class Session:
    def __init__(self, replies):
        self.headers, self.calls, self.replies = {}, [], replies

    def get(self, url, **kwargs):
        assert kwargs["allow_redirects"] is False
        self.calls.append(url)
        reply = self.replies[url]
        if isinstance(reply, Exception):
            raise reply
        r = requests.Response()
        r.status_code, text, headers = reply
        r._content = text.encode()
        r._content_consumed = True
        r.encoding = "utf-8"
        r.headers.update(headers)
        r.url = url
        return r


def client(replies):
    return Client(session=Session(replies), sleeper=lambda _: None, clock=lambda: 0)


def test_disallowed_never_requests_content():
    c = client({"https://program.kbs.co.kr/robots.txt": (200, "User-agent: *\nDisallow: /test", {})})
    with pytest.raises(AccessError, match="robots_disallowed"):
        c.get_html(URL)
    assert c.session.calls == ["https://program.kbs.co.kr/robots.txt"]


def test_proxy_failure_stops_and_does_not_leak_exception():
    c = client({"https://program.kbs.co.kr/robots.txt": requests.exceptions.ProxyError("credential=SECRET")})
    with pytest.raises(AccessError) as error:
        c.get_html(URL)
    assert error.value.kind == "proxy_error"
    assert "SECRET" not in str(c.audit)
    assert len(c.session.calls) == 1


def test_missing_robots_can_fetch_and_policy_cached():
    c = client({"https://program.kbs.co.kr/robots.txt": (404, "", {}),
                URL: (200, "<article>테스트</article>", {"Content-Type": "text/html"})})
    assert "테스트" in c.get_html(URL)
    c.get_html(URL)
    assert c.session.calls.count("https://program.kbs.co.kr/robots.txt") == 1


def test_destination_robots_checked_on_redirect():
    c = client({"https://program.kbs.co.kr/robots.txt": (200, "User-agent: *\nDisallow:", {}),
                URL: (302, "", {"Location": "https://pbbs.kbs.co.kr/private"}),
                "https://pbbs.kbs.co.kr/robots.txt": (200, "User-agent: *\nDisallow: /", {})})
    with pytest.raises(AccessError, match="robots_disallowed"):
        c.get_html(URL)
    assert "https://pbbs.kbs.co.kr/private" not in c.session.calls


@pytest.mark.parametrize("url", ["http://program.kbs.co.kr/", "https://program.kbs.co.kr.evil.org/", "https://user:secret@program.kbs.co.kr/", "https://127.0.0.1/", "https://program.kbs.co.kr:444/"])
def test_host_boundary(url):
    with pytest.raises(ValueError):
        validate_url(url)


@pytest.mark.parametrize("status", [401, 403, 429, 500])
def test_unavailable_robots_fail_closed(status):
    c = client({"https://program.kbs.co.kr/robots.txt": (status, "", {})})
    with pytest.raises(AccessError, match="robots_unavailable"):
        c.get_html(URL)
    assert len(c.session.calls) == 1


def test_robots_html_is_not_a_policy():
    c = client({"https://program.kbs.co.kr/robots.txt": (200, "<!doctype html><html>로그인</html>", {})})
    with pytest.raises(AccessError, match="robots_unreadable"):
        c.get_html(URL)


@pytest.mark.parametrize("url", ["https://program.kbs.co.kr/x\n", "https://program.kbs.co.kr/a>b", "https://program.kbs.co.kr/a\\b"])
def test_invalid_url_characters(url):
    with pytest.raises(ValueError):
        validate_url(url)


def test_iaudience_requires_permission_even_when_robots_allows():
    c = client({"https://iaudience.kbs.co.kr/robots.txt": (200, "User-agent: *\nDisallow:", {})})
    with pytest.raises(AccessError, match="policy_review_required"):
        c.get_html("https://iaudience.kbs.co.kr/broadcast/11344")
    assert c.session.calls == ["https://iaudience.kbs.co.kr/robots.txt"]
