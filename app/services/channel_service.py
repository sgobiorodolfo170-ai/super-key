import json
import time
import asyncio
import logging
from datetime import datetime
import httpx
from sqlalchemy import select
from app.database import async_session
from app.models.channel import Channel
from app.models.ability import Ability
from app.utils.crypto import encrypt_api_key, decrypt_api_key

logger = logging.getLogger(__name__)


class ChannelService:

    @staticmethod
    async def auto_config(channel_id: int) -> dict:
        async with async_session() as session:
            channel = await session.get(Channel, channel_id)
            if not channel:
                return {"error": "Channel not found"}

            api_key = decrypt_api_key(channel.api_key)
            base_url = (channel.api_base or "").rstrip("/")

            result = await ChannelService._probe_api(base_url, api_key)
            return result

    @staticmethod
    async def _probe_api(base_url: str, api_key: str) -> dict:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
            async def probe_openai():
                try:
                    resp = await client.get(
                        f"{base_url}/v1/models",
                        headers={"Authorization": f"Bearer {api_key}"},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        models = [m["id"] for m in data.get("data", [])]
                        return {"api_type": "openai", "models": models, "detected": "openai_compatible", "model_count": len(models)}
                except Exception as e:
                    logger.warning("OpenAI-compatible probe failed for %s: %s", base_url, e)
                return None

            async def probe_gemini():
                try:
                    resp = await client.get(
                        f"{base_url}/v1beta/models?key={api_key}",
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        models = []
                        for m in data.get("models", []):
                            name = m.get("name", "")
                            if "/" in name:
                                models.append(name.split("/")[-1])
                            else:
                                models.append(name)
                        return {"api_type": "gemini", "models": models, "detected": "gemini", "model_count": len(models)}
                except Exception as e:
                    logger.warning("Gemini probe failed for %s: %s", base_url, e)
                return None

            results = await asyncio.gather(probe_openai(), probe_gemini())
            for result in results:
                if result:
                    return result

            logger.info("API probe for %s: unknown format", base_url)
            return {"api_type": "custom", "models": [], "detected": "unknown", "model_count": 0}

    @staticmethod
    async def test_channel(channel_id: int) -> dict:
        async with async_session() as session:
            channel = await session.get(Channel, channel_id)
            if not channel:
                return {"error": "Channel not found"}

            api_key = decrypt_api_key(channel.api_key)
            if not api_key:
                return {"success": False, "error": "API Key is empty or decryption failed. Please re-enter the API Key in channel settings."}

            base_url = (channel.api_base or "").rstrip("/")
            if not base_url:
                return {"success": False, "error": "API Base URL is empty. Please configure the base URL in channel settings."}

            # 获取测试模型：优先使用指定的测试模型，否则取渠道第一个模型，最后使用默认值
            test_model = channel.test_model
            if not test_model:
                if channel.models:
                    first_model = channel.models.split(",")[0].strip()
                    test_model = first_model if first_model else "gpt-3.5-turbo"
                else:
                    test_model = "gpt-3.5-turbo"

            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                try:
                    start = time.time()
                    resp = await client.post(
                        f"{base_url}/v1/chat/completions",
                        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                        json={"model": test_model, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1},
                    )
                    elapsed = (time.time() - start) * 1000

                    channel.response_time = int(elapsed)
                    channel.last_test_time = datetime.now()
                    if resp.status_code == 200:
                        channel.status = 1
                    await session.commit()
                    if resp.status_code == 200:
                        logger.info("Channel %d test success: model=%s, latency=%dms", channel_id, test_model, int(elapsed))
                        return {"success": True, "model": test_model, "response_time_ms": int(elapsed), "status_code": resp.status_code}
                    else:
                        logger.warning("Channel %d test failed: model=%s, status=%d, body=%s", channel_id, test_model, resp.status_code, resp.text[:200])
                        return {"success": False, "model": test_model, "status_code": resp.status_code, "message": resp.text[:200]}
                except Exception as e:
                    logger.error("Channel %d test exception: model=%s, error=%s", channel_id, test_model, str(e))
                    return {"success": False, "model": test_model, "error": str(e)}

    @staticmethod
    async def sync_abilities(channel_id: int, models: list[str]):
        async with async_session() as session:
            from sqlalchemy import delete
            await session.execute(delete(Ability).where(Ability.channel_id == channel_id))
            if models:
                abilities = [Ability(channel_id=channel_id, model=model, enabled=True) for model in models]
                session.add_all(abilities)
            await session.commit()
