from types import SimpleNamespace

import pytest

from insta_studio import generator

DRAFT = generator.PostDraft(
    summary=["요약1", "요약2", "요약3"],
    titles=["지난 은메달의 아쉬움\n*허미미*, 금메달", "b", "c"],
    caption="첫 줄\n\n출처: 테스트뉴스",
    hashtags=["#유도", "허미미", " # ", "금메달"],
    source_label="출처: 테스트뉴스",
    cautions=[],
)


class FakeMessages:
    def __init__(self, response):
        self.response = response
        self.kwargs = None

    def parse(self, **kwargs):
        self.kwargs = kwargs
        return self.response


def fake_client(response):
    messages = FakeMessages(response)
    return SimpleNamespace(beta=SimpleNamespace(messages=messages)), messages


def test_generate_post_returns_clean_draft():
    client, messages = fake_client(SimpleNamespace(stop_reason="end_turn", parsed_output=DRAFT.model_copy()))
    draft = generator.generate_post("원문 " * 30, source="테스트뉴스", tone="warm", client=client)
    assert draft.hashtags == ["유도", "허미미", "금메달"]
    assert messages.kwargs["output_format"] is generator.PostDraft
    assert messages.kwargs["fallbacks"] == "default"
    content = messages.kwargs["messages"][0]["content"]
    assert "테스트뉴스" in content and "공감" in content


def test_refusal_raises():
    client, _ = fake_client(SimpleNamespace(stop_reason="refusal", parsed_output=None))
    with pytest.raises(generator.GenerationError):
        generator.generate_post("원문 " * 30, client=client)


def test_short_text_rejected_without_calling_api():
    client, messages = fake_client(None)
    with pytest.raises(generator.GenerationError):
        generator.generate_post("짧다", client=client)
    assert messages.kwargs is None
