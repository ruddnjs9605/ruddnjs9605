"""Publish a single image post through the Instagram Graph API (content publishing).

Requires an Instagram professional (business/creator) account and a long-lived
access token with content-publish permission. Instagram downloads the image
itself, so the image must be reachable at a public HTTPS URL.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

import requests


class InstagramError(Exception):
    pass


@dataclass
class InstagramConfig:
    user_id: str
    access_token: str
    graph_base: str = "https://graph.facebook.com/v21.0"

    @classmethod
    def from_env(cls) -> "InstagramConfig | None":
        user_id = os.environ.get("IG_USER_ID", "").strip()
        token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
        if not (user_id and token):
            return None
        base = os.environ.get("IG_GRAPH_BASE", "").strip() or cls.graph_base
        return cls(user_id=user_id, access_token=token, graph_base=base.rstrip("/"))


def _call(method: str, url: str, **params) -> dict:
    try:
        resp = requests.request(method, url, data=params if method == "POST" else None,
                                params=params if method == "GET" else None, timeout=30)
    except requests.RequestException as exc:
        raise InstagramError(f"Instagram API 연결 실패: {exc}") from exc
    try:
        data = resp.json()
    except ValueError:
        data = {}
    if resp.status_code >= 400 or "error" in data:
        message = (data.get("error") or {}).get("message") or resp.text[:200]
        raise InstagramError(f"Instagram API 오류: {message}")
    return data


def publish_image(cfg: InstagramConfig, image_url: str, caption: str,
                  poll_interval: float = 2.0, max_polls: int = 15) -> str:
    """Create a media container, wait until it is ready, publish it. Returns the media id."""
    base = f"{cfg.graph_base}/{cfg.user_id}"
    container = _call("POST", f"{base}/media", image_url=image_url, caption=caption,
                      access_token=cfg.access_token)
    creation_id = container.get("id")
    if not creation_id:
        raise InstagramError("Instagram이 미디어 컨테이너 ID를 돌려주지 않았습니다.")

    for _ in range(max_polls):
        status = _call("GET", f"{cfg.graph_base}/{creation_id}", fields="status_code",
                       access_token=cfg.access_token).get("status_code")
        if status in (None, "FINISHED"):
            break
        if status in ("ERROR", "EXPIRED"):
            raise InstagramError(f"Instagram이 이미지를 처리하지 못했습니다 ({status}).")
        time.sleep(poll_interval)
    else:
        raise InstagramError("Instagram 이미지 처리가 너무 오래 걸립니다. 잠시 후 다시 시도하세요.")

    published = _call("POST", f"{base}/media_publish", creation_id=creation_id,
                      access_token=cfg.access_token)
    media_id = published.get("id")
    if not media_id:
        raise InstagramError("게시 결과 ID를 받지 못했습니다.")
    return media_id
