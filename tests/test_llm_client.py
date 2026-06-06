import pytest
from src.llm.client import LLMClient


@pytest.mark.asyncio
async def test_llm_client_returns_string():
    client = LLMClient()
    result = await client.chat("Say hello", "Say hello in Chinese")
    assert isinstance(result, str)
    assert len(result) > 0
