import pytest
from fastapi.testclient import TestClient

from insta_studio import app as app_module, generator, instagram


@pytest.fixture
def client(monkeypatch, tmp_path):
    for key in ("APP_PASSWORD", "IG_USER_ID", "IG_ACCESS_TOKEN", "PUBLIC_BASE_URL", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(app_module, "MEDIA_DIR", tmp_path)
    return TestClient(app_module.app)


def test_index_and_config(client):
    assert "Insta Studio" in client.get("/").text
    cfg = client.get("/api/config").json()
    assert cfg["instagram_ready"] is False
    assert "info" in cfg["tones"]


def test_password_protects_api(client, monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", "secret")
    assert client.post("/api/generate", json={"text": "x"}).status_code == 401
    r = client.post("/api/generate", json={"text": "x"}, headers={"X-App-Password": "secret"})
    assert r.status_code == 422  # passes auth, fails on short text


def test_generate_endpoint(client, monkeypatch):
    draft = generator.PostDraft(summary=["a"], titles=["t"], caption="c", hashtags=["h"],
                                source_label="s", cautions=[])
    monkeypatch.setattr(generator, "generate_post", lambda text, **kw: draft)
    assert client.post("/api/generate", json={"text": "본문" * 20}).json()["titles"] == ["t"]


def test_publish_requires_config(client):
    r = client.post("/api/publish", files={"image": ("p.jpg", b"\xff\xd8xx", "image/jpeg")}, data={"caption": "c"})
    assert r.status_code == 400


def test_publish_saves_jpeg_and_calls_instagram(client, monkeypatch, tmp_path):
    monkeypatch.setenv("IG_USER_ID", "1")
    monkeypatch.setenv("IG_ACCESS_TOKEN", "tok")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://studio.example.com/")
    calls = {}

    def fake_publish(cfg, image_url, caption):
        calls.update(image_url=image_url, caption=caption)
        return "999"

    monkeypatch.setattr(instagram, "publish_image", fake_publish)
    r = client.post("/api/publish", files={"image": ("p.jpg", b"\xff\xd8jpegdata", "image/jpeg")},
                    data={"caption": "캡션"})
    assert r.json() == {"media_id": "999"}
    name = calls["image_url"].rsplit("/", 1)[1]
    assert calls["image_url"] == f"https://studio.example.com/media/{name}"
    assert client.get(f"/media/{name}").content == b"\xff\xd8jpegdata"


def test_publish_rejects_png(client, monkeypatch):
    monkeypatch.setenv("IG_USER_ID", "1")
    monkeypatch.setenv("IG_ACCESS_TOKEN", "tok")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://studio.example.com")
    r = client.post("/api/publish", files={"image": ("p.png", b"\x89PNG", "image/png")}, data={"caption": "c"})
    assert r.status_code == 400


def test_media_path_traversal_blocked(client):
    assert client.get("/media/..%2F..%2Fetc%2Fpasswd").status_code == 404
