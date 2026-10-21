"""Turn source text into an Instagram post draft with Claude."""

from __future__ import annotations

import os

import anthropic
from pydantic import BaseModel, Field

MODEL = os.environ.get("INSTA_STUDIO_MODEL", "claude-opus-5-5")

TONES = {
    "info": "정보 전달형: 핵심 사실을 깔끔하고 신뢰감 있게 전달한다.",
    "curious": "호기심 유발형: 궁금증을 자극하되, 본문에 없는 내용을 과장하거나 지어내지 않는다.",
    "warm": "공감·감동형: 사람들의 감정에 공감하는 따뜻한 말투로 쓴다.",
}

SYSTEM_PROMPT = """너는 한국어 인스타그램 이슈·정보 계정의 에디터다.
사용자가 준 원문(뉴스 기사, 커뮤니티 글 등)을 읽고 인스타그램 이미지 게시물 초안을 만든다.

규칙:
- 원문에 있는 사실만 쓴다. 숫자, 이름, 날짜, 인용을 지어내거나 바꾸지 않는다.
- 원문이 불확실하거나 논란이 있는 내용이면 단정하지 말고 "~라고 전해졌다", "~라는 주장" 처럼 쓴다.
- 특정 개인을 조롱하거나 혐오·비하하는 표현을 쓰지 않는다.
- 원문 문장을 길게 그대로 베끼지 말고 자기 말로 다시 정리한다.
- 이미지 제목은 사진 아래 검은 그라데이션 위에 가운데 정렬로 2~3줄 들어간다.
  한 줄은 공백 포함 14자 안팎으로 끊고 줄 사이에 \\n 을 넣는다. 예: "지난 은메달의 아쉬움\\n할머니와의 약속 안고\\n허미미, 나고야서 금메달"
- 제목에서 가장 강조할 핵심 키워드 1개(최대 2개)를 *별표*로 감싼다. 이 부분은 빨간 글씨로 표시된다. 예: "*허미미*, 나고야서 금메달"
- 캡션 첫 줄은 피드에서 '더 보기' 전에 보이므로 가장 중요한 한 문장으로 시작한다.
- 캡션은 짧은 문단과 줄바꿈으로 읽기 쉽게 구성하고, 이모지는 적당히(0~4개) 쓴다.
- 캡션 마지막 줄에 출처를 "출처: 매체/사이트명"으로 적는다. 출처를 모르면 "출처: 원문 링크 참고"로 적는다.
- 해시태그는 '#' 없이 단어만, 관련성 높은 것으로 8~15개.
"""


class PostDraft(BaseModel):
    summary: list[str] = Field(description="원문 핵심 요약, 3~5개 bullet 문장")
    titles: list[str] = Field(description="이미지에 올릴 제목 후보 3개. 줄바꿈은 \\n, 강조 키워드는 *별표*")
    caption: str = Field(description="인스타그램 본문 캡션(해시태그 제외)")
    hashtags: list[str] = Field(description="해시태그 8~15개, # 없이")
    source_label: str = Field(description="이미지 하단에 표기할 짧은 출처 표기, 예: '출처: 연합뉴스'")
    cautions: list[str] = Field(
        description="게시 전 사용자가 확인해야 할 점(사실 확인 필요, 저작권, 민감한 주제 등). 없으면 빈 배열"
    )


class GenerationError(Exception):
    pass


def build_user_message(text: str, title: str = "", source: str = "", url: str = "", tone: str = "info") -> str:
    parts = [f"톤: {TONES.get(tone, TONES['info'])}"]
    if source:
        parts.append(f"출처(매체/사이트): {source}")
    if url:
        parts.append(f"원문 링크: {url}")
    if title:
        parts.append(f"원문 제목: {title}")
    parts.append(f"<원문>\n{text}\n</원문>")
    return "\n\n".join(parts)


def generate_post(
    text: str,
    *,
    title: str = "",
    source: str = "",
    url: str = "",
    tone: str = "info",
    client: anthropic.Anthropic | None = None,
) -> PostDraft:
    if len(text.strip()) < 30:
        raise GenerationError("원문 내용이 너무 짧습니다. 기사나 글 본문을 더 넣어 주세요.")
    client = client or anthropic.Anthropic()
    try:
        response = client.beta.messages.parse(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_user_message(text, title, source, url, tone)}],
            output_format=PostDraft,
            output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.AuthenticationError as exc:
        raise GenerationError("Anthropic API 키가 올바르지 않습니다. ANTHROPIC_API_KEY를 확인하세요.") from exc
    except anthropic.RateLimitError as exc:
        raise GenerationError("요청이 너무 많습니다. 잠시 후 다시 시도하세요.") from exc
    except anthropic.APIConnectionError as exc:
        raise GenerationError("Anthropic API에 연결할 수 없습니다.") from exc
    except anthropic.APIStatusError as exc:
        raise GenerationError(f"AI 생성 중 오류가 발생했습니다 (HTTP {exc.status_code}).") from exc

    if response.stop_reason == "refusal":
        raise GenerationError("AI가 이 내용으로는 게시물을 만들 수 없다고 응답했습니다. 다른 소재를 사용해 주세요.")
    if response.stop_reason == "max_tokens" or response.parsed_output is None:
        raise GenerationError("AI 응답이 완성되지 않았습니다. 원문을 줄여서 다시 시도하세요.")
    draft = response.parsed_output
    draft.hashtags = [h.lstrip("#").strip() for h in draft.hashtags if h.strip("# ")]
    return draft
