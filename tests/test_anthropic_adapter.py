"""Anthropic アダプターのテスト（API は呼ばず、SDK クライアントをモックする）"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from yamii.adapters.ai.anthropic import AnthropicAdapter, AnthropicAdapterWithFallback
from yamii.domain.ports.ai_port import ChatMessage


def _response(text: str, stop_reason: str = "end_turn"):
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=[
            SimpleNamespace(type="thinking", thinking=""),
            SimpleNamespace(type="text", text=text),
        ],
    )


def _client(response):
    client = MagicMock()
    client.beta.messages.create = AsyncMock(return_value=response)
    return client


@pytest.mark.asyncio
async def test_generate_sends_messages_api_request():
    client = _client(_response("こんにちは"))
    adapter = AnthropicAdapter(
        api_key="test", model="claude-sonnet-5-5", enable_anonymization=False, client=client
    )

    result = await adapter.generate(
        "相談です",
        "あなたはカウンセラーです",
        max_tokens=200,
        conversation_history=[
            ChatMessage(role="user", content="前の質問"),
            ChatMessage(role="assistant", content="前の回答"),
        ],
    )

    assert result == "こんにちは"
    kwargs = client.beta.messages.create.call_args.kwargs
    assert kwargs["model"] == "claude-sonnet-5-5"
    assert kwargs["system"] == "あなたはカウンセラーです"
    assert kwargs["max_tokens"] == 200
    assert kwargs["messages"] == [
        {"role": "user", "content": "前の質問"},
        {"role": "assistant", "content": "前の回答"},
        {"role": "user", "content": "相談です"},
    ]
    assert kwargs["thinking"] == {"type": "between_tools"}
    assert kwargs["fallbacks"] == "default"
    assert kwargs["betas"] == ["server-side-fallback-2026-07-01"]


@pytest.mark.asyncio
async def test_generate_uses_default_max_tokens():
    client = _client(_response("ok"))
    adapter = AnthropicAdapter(api_key="test", enable_anonymization=False, client=client)

    await adapter.generate("hi", "sys")

    assert client.beta.messages.create.call_args.kwargs["max_tokens"] == 16000


@pytest.mark.asyncio
async def test_generate_raises_on_refusal():
    client = _client(_response("", stop_reason="refusal"))
    adapter = AnthropicAdapter(api_key="test", enable_anonymization=False, client=client)

    with pytest.raises(Exception, match="refusal"):
        await adapter.generate("hi", "sys")


@pytest.mark.asyncio
async def test_fallback_adapter_returns_fallback_message_on_error():
    client = _client(_response("", stop_reason="refusal"))
    adapter = AnthropicAdapterWithFallback(
        api_key="test", enable_anonymization=False, client=client, fallback_message="fallback"
    )

    assert await adapter.generate("hi", "sys") == "fallback"


@pytest.mark.asyncio
async def test_generate_stream_yields_text():
    async def text_stream():
        for chunk in ["こん", "にちは"]:
            yield chunk

    stream = MagicMock()
    stream.__aenter__ = AsyncMock(return_value=SimpleNamespace(text_stream=text_stream()))
    stream.__aexit__ = AsyncMock(return_value=None)
    client = MagicMock()
    client.beta.messages.stream = MagicMock(return_value=stream)
    adapter = AnthropicAdapter(api_key="test", enable_anonymization=False, client=client)

    chunks = [c async for c in adapter.generate_stream("hi", "sys")]

    assert "".join(chunks) == "こんにちは"
    kwargs = client.beta.messages.stream.call_args.kwargs
    assert kwargs["thinking"] == {"type": "between_tools"}


def test_model_name():
    adapter = AnthropicAdapter(api_key="test", model="claude-sonnet-5-5", client=MagicMock())
    assert adapter.model_name == "claude-sonnet-5-5"
