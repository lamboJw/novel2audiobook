import json
import asyncio
from openai import AsyncOpenAI
from src.config import LLM_BASE_URL, LLM_MODEL, LLM_TIMEOUT, LLM_MAX_CONCURRENCY, LLM_API_KEY


class LLMClient:
    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=LLM_BASE_URL,
            api_key=LLM_API_KEY,
            timeout=LLM_TIMEOUT,
        )
        self.model = LLM_MODEL
        self.semaphore = asyncio.Semaphore(LLM_MAX_CONCURRENCY)

    async def chat(self, system_prompt: str, user_prompt: str, max_retries: int = 3) -> str:
        for attempt in range(max_retries):
            try:
                async with self.semaphore:
                    resp = await self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.3,
                        max_tokens=4096,
                    )
                    return resp.choices[0].message.content
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2**attempt)

    async def chat_json(self, system_prompt: str, user_prompt: str) -> dict:
        text = await self.chat(system_prompt, user_prompt)
        if text.startswith("```"):
            text = text.strip("`").removeprefix("json").strip()
        return json.loads(text)
