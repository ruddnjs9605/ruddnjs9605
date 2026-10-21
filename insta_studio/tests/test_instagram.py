from insta_studio import instagram


def test_publish_flow(monkeypatch):
    seen = []

    def fake_call(method, url, **params):
        seen.append((method, url, params))
        if url.endswith("/media"):
            return {"id": "c1"}
        if url.endswith("/c1"):
            return {"status_code": "FINISHED"}
        return {"id": "m1"}

    monkeypatch.setattr(instagram, "_call", fake_call)
    cfg = instagram.InstagramConfig(user_id="42", access_token="tok", graph_base="https://graph.test/v1")
    assert instagram.publish_image(cfg, "https://img/x.jpg", "cap", poll_interval=0) == "m1"
    assert seen[0] == ("POST", "https://graph.test/v1/42/media",
                       {"image_url": "https://img/x.jpg", "caption": "cap", "access_token": "tok"})
    assert seen[-1][1] == "https://graph.test/v1/42/media_publish"
    assert seen[-1][2]["creation_id"] == "c1"
