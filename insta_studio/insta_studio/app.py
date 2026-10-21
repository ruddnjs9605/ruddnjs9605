"""FastAPI server: source → AI draft → image composer → Instagram."""

from __future__ import annotations

import hmac
import os
import re
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import fetcher, generator, instagram

STATIC_DIR = Path(__file__).parent / "static"
MEDIA_DIR = Path(os.environ.get("INSTA_STUDIO_MEDIA_DIR", "media")).resolve()
MAX_UPLOAD_BYTES = 8 * 1024 * 1024


def require_password(x_app_password: str = Header(default="")) -> None:
    expected = os.environ.get("APP_PASSWORD", "")
    if expected and not hmac.compare_digest(x_app_password, expected):
        raise HTTPException(401, "비밀번호가 필요합니다.")


app = FastAPI(title="Insta Studio")
api = Depends(require_password)


class ExtractRequest(BaseModel):
    url: str


class GenerateRequest(BaseModel):
    text: str
    title: str = ""
    source: str = ""
    url: str = ""
    tone: str = "info"


def _public_base_url() -> str:
    return os.environ.get("PUBLIC_BASE_URL", "").strip().rstrip("/")


@app.get("/api/config")
def config():
    return {
        "ai_ready": bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")),
        "instagram_ready": bool(instagram.InstagramConfig.from_env() and _public_base_url()),
        "password_required": bool(os.environ.get("APP_PASSWORD")),
        "tones": generator.TONES,
    }


@app.post("/api/extract", dependencies=[api])
def extract(req: ExtractRequest):
    try:
        article = fetcher.fetch_article(req.url.strip())
    except fetcher.FetchError as exc:
        raise HTTPException(422, str(exc)) from exc
    return article.__dict__


@app.post("/api/generate", dependencies=[api])
def generate(req: GenerateRequest):
    try:
        draft = generator.generate_post(
            req.text[: fetcher.MAX_ARTICLE_CHARS], title=req.title, source=req.source, url=req.url, tone=req.tone
        )
    except generator.GenerationError as exc:
        raise HTTPException(422, str(exc)) from exc
    return draft.model_dump()


@app.get("/api/image-proxy", dependencies=[api])
def image_proxy(url: str):
    """Serve a remote image from our origin so the browser canvas can export it."""
    try:
        body, content_type = fetcher.fetch_image(url)
    except fetcher.FetchError as exc:
        raise HTTPException(422, str(exc)) from exc
    return Response(body, media_type=content_type, headers={"Cache-Control": "private, max-age=600"})


@app.post("/api/publish", dependencies=[api])
async def publish(image: UploadFile = File(...), caption: str = Form(...)):
    cfg = instagram.InstagramConfig.from_env()
    base = _public_base_url()
    if not (cfg and base):
        raise HTTPException(400, "Instagram 자동 게시가 설정되지 않았습니다 (IG_USER_ID, IG_ACCESS_TOKEN, PUBLIC_BASE_URL).")
    data = await image.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "이미지가 너무 큽니다 (최대 8MB).")
    if not data.startswith(b"\xff\xd8"):
        raise HTTPException(400, "Instagram은 JPEG 이미지만 받습니다.")
    if len(caption) > 2200:
        raise HTTPException(400, "캡션은 2,200자 이하여야 합니다.")

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.jpg"
    (MEDIA_DIR / name).write_bytes(data)
    try:
        media_id = instagram.publish_image(cfg, f"{base}/media/{name}", caption)
    except instagram.InstagramError as exc:
        raise HTTPException(502, str(exc)) from exc
    return {"media_id": media_id}


@app.get("/media/{name}")
def media(name: str):
    if not re.fullmatch(r"[0-9a-f]{32}\.jpg", name) or not (MEDIA_DIR / name).is_file():
        raise HTTPException(404)
    return FileResponse(MEDIA_DIR / name, media_type="image/jpeg")


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
