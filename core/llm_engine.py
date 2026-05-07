import aiohttp
import asyncio
import json
from typing import Optional, AsyncGenerator


class LLMEngine:
    def __init__(self, model: str = "deepseek-coder:7b", host: str = "http://localhost:11434"):
        self.model = model
        self.host = host
        self.endpoint = f"{host}/api/generate"
        self.timeout = aiohttp.ClientTimeout(total=300)

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: int = 4096,
        stream: bool = False,
    ) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "temperature": temperature,
            "top_p": top_p,
            "num_predict": max_tokens,
            "stream": stream,
        }

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(self.endpoint, json=payload) as response:
                if response.status != 200:
                    raise RuntimeError(
                        f"LLM request failed: {response.status} {await response.text()}"
                    )

                if stream:
                    return await self._handle_stream(response)
                else:
                    data = await response.json()
                    return data.get("response", "")

    async def generate_stream(
        self,
        prompt: str,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "temperature": temperature,
            "stream": True,
        }

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(self.endpoint, json=payload) as response:
                if response.status != 200:
                    raise RuntimeError(f"LLM request failed: {response.status}")

                async for line in response.content:
                    try:
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]
                    except json.JSONDecodeError:
                        continue

    async def _handle_stream(self, response) -> str:
        result = ""
        async for line in response.content:
            try:
                data = json.loads(line)
                if "response" in data:
                    result += data["response"]
            except json.JSONDecodeError:
                continue
        return result

    async def check_health(self) -> bool:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(f"{self.host}/api/tags") as response:
                    return response.status == 200
        except:
            return False
