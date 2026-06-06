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

    async def chat_json(self, system_prompt: str, user_prompt: str) -> dict | list:
        text = await self.chat(system_prompt, user_prompt)
        return self._extract_json(text)

    @staticmethod
    def _extract_json(text: str) -> dict | list:
        import re
        text = text.strip()
        # try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # try extracting from markdown code block
        m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1).strip())
            except json.JSONDecodeError:
                pass
        # try finding first array or object
        for start, end, brace in [(text.find("["), text.rfind("]"), "[]"),
                                   (text.find("{"), text.rfind("}"), "{}")]:
            if start != -1 and end > start:
                try:
                    return json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    pass
        raise json.JSONDecodeError(f"Failed to extract JSON from: {text[:200]}...", text, 0)
