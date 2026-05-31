import json
import os
import logging
import secrets
from sqlalchemy import select, func
from app.database import async_session
from app.models.provider import Provider
from app.models.model_classification import ModelClassification
from app.models.admin_user import AdminUser
from app.config import settings

logger = logging.getLogger(__name__)


class PresetService:

    PRESETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "presets")

    @staticmethod
    async def load_all_if_empty():
        async with async_session() as session:
            provider_count = await session.scalar(select(func.count()).select_from(Provider))
            if provider_count == 0:
                await PresetService.load_providers(session)

            model_count = await session.scalar(select(func.count()).select_from(ModelClassification))
            if model_count == 0:
                await PresetService.load_models(session)

            admin_count = await session.scalar(select(func.count()).select_from(AdminUser))
            if admin_count == 0:
                await PresetService.create_default_admin(session)

    @staticmethod
    async def load_providers(session=None):
        providers = PresetService._get_builtin_providers()
        logger.info("Loading %d builtin providers", len(providers))
        codes = {p["code"] for p in providers}

        async def _do_load(sess):
            existing_result = await sess.execute(
                select(Provider.code).where(Provider.code.in_(codes))
            )
            existing_codes = {row[0] for row in existing_result.all()}

            new_providers = [Provider(**p) for p in providers if p["code"] not in existing_codes]
            if new_providers:
                sess.add_all(new_providers)
                await sess.commit()
                logger.info("Inserted %d new builtin providers", len(new_providers))
            else:
                logger.info("All %d builtin providers already exist", len(providers))

        if session is None:
            async with async_session() as session:
                await _do_load(session)
        else:
            await _do_load(session)

    @staticmethod
    async def load_models(session=None):
        models = PresetService._get_builtin_models()
        logger.info("Loading %d builtin models", len(models))
        model_ids = {m["model_id"] for m in models}

        async def _do_load(sess):
            existing_result = await sess.execute(
                select(ModelClassification.model_id).where(ModelClassification.model_id.in_(model_ids))
            )
            existing_ids = {row[0] for row in existing_result.all()}

            new_models = [ModelClassification(**m) for m in models if m["model_id"] not in existing_ids]
            if new_models:
                sess.add_all(new_models)
                await sess.commit()
                logger.info("Inserted %d new builtin models", len(new_models))
            else:
                logger.info("All %d builtin models already exist", len(models))

        if session is None:
            async with async_session() as session:
                await _do_load(session)
        else:
            await _do_load(session)

    @staticmethod
    async def create_default_admin(session=None):
        password = settings.default_admin_password or secrets.token_urlsafe(16)
        username = "admin"
        
        if session is None:
            async with async_session() as session:
                admin_user = AdminUser(
                    username=username,
                    password_hash=AdminUser.hash_password(password),
                    email="admin@example.com",
                    is_active=True
                )
                session.add(admin_user)
                await session.commit()
        else:
            admin_user = AdminUser(
                username=username,
                password_hash=AdminUser.hash_password(password),
                email="admin@example.com",
                is_active=True
            )
            session.add(admin_user)
            await session.commit()
        
        if not settings.default_admin_password:
            logger.warning("Default admin password generated: %s (set SUPER_KEY_DEFAULT_ADMIN_PASSWORD to customize)", password)
        else:
            logger.info("Default admin created with configured password")

    @staticmethod
    def _get_builtin_providers():
        return [
            {"name": "OpenAI", "code": "openai", "website": "https://openai.com", "description": "OpenAI 官方 API，提供 GPT 系列模型", "api_base": "https://api.openai.com/v1", "api_docs_url": "https://platform.openai.com/docs", "is_builtin": True, "is_active": True},
            {"name": "Google Gemini", "code": "google", "website": "https://ai.google.dev", "description": "Google Gemini 多模态大模型", "api_base": "https://generativelanguage.googleapis.com", "api_docs_url": "https://ai.google.dev/docs", "is_builtin": True, "is_active": True},
            {"name": "Anthropic Claude", "code": "anthropic", "website": "https://anthropic.com", "description": "Anthropic Claude 系列模型", "api_base": "https://api.anthropic.com", "api_docs_url": "https://docs.anthropic.com", "is_builtin": True, "is_active": True},
            {"name": "DeepSeek", "code": "deepseek", "website": "https://deepseek.com", "description": "DeepSeek 深度求索大模型", "api_base": "https://api.deepseek.com/v1", "api_docs_url": "https://platform.deepseek.com/docs", "is_builtin": True, "is_active": True},
            {"name": "阿里云通义千问", "code": "alibaba", "website": "https://tongyi.aliyun.com", "description": "阿里云百炼平台，提供通义千问系列模型", "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1", "api_docs_url": "https://help.aliyun.com/document_detail/2712195.html", "is_builtin": True, "is_active": True},
            {"name": "字节跳动豆包", "code": "bytedance", "website": "https://www.volcengine.com/product/doubao", "description": "火山引擎豆包大模型", "api_base": "https://ark.cn-beijing.volces.com/api/v3", "api_docs_url": "https://www.volcengine.com/docs/82379", "is_builtin": True, "is_active": True},
            {"name": "智谱AI", "code": "zhipu", "website": "https://open.bigmodel.cn", "description": "智谱AI开放平台，提供GLM系列模型", "api_base": "https://open.bigmodel.cn/api/paas/v4", "api_docs_url": "https://open.bigmodel.cn/dev/api", "is_builtin": True, "is_active": True},
            {"name": "百度文心一言", "code": "baidu", "website": "https://yiyan.baidu.com", "description": "百度智能云千帆大模型平台", "api_base": "https://qianfan.baidubce.com/v2", "api_docs_url": "https://cloud.baidu.com/doc/WENXINWORKSHOP/index.html", "is_builtin": True, "is_active": True},
            {"name": "月之暗面 Moonshot", "code": "moonshot", "website": "https://www.moonshot.cn", "description": "月之暗面 Kimi 大模型平台", "api_base": "https://api.moonshot.cn/v1", "api_docs_url": "https://platform.moonshot.cn/docs", "is_builtin": True, "is_active": True},
            {"name": "阶跃星辰", "code": "stepfun", "website": "https://www.stepfun.com", "description": "阶跃星辰 Step 系列大模型", "api_base": "https://api.stepfun.com/v1", "api_docs_url": "https://platform.stepfun.com/docs", "is_builtin": True, "is_active": True},
            {"name": "MiniMax", "code": "minimax", "website": "https://www.minimaxi.com", "description": "MiniMax 大模型平台", "api_base": "https://api.minimax.chat/v1", "api_docs_url": "https://platform.minimaxi.com", "is_builtin": True, "is_active": True},
            {"name": "零一万物", "code": "01ai", "website": "https://www.lingyiwanwu.com", "description": "零一万物 Yi 系列大模型", "api_base": "https://api.lingyiwanwu.com/v1", "api_docs_url": "https://platform.lingyiwanwu.com/docs", "is_builtin": True, "is_active": True},
            {"name": "Mistral", "code": "mistral", "website": "https://mistral.ai", "description": "Mistral AI 大模型平台", "api_base": "https://api.mistral.ai/v1", "api_docs_url": "https://docs.mistral.ai", "is_builtin": True, "is_active": True},
            {"name": "Cohere", "code": "cohere", "website": "https://cohere.com", "description": "Cohere 企业级大模型平台", "api_base": "https://api.cohere.com/v1", "api_docs_url": "https://docs.cohere.com", "is_builtin": True, "is_active": True},
            {"name": "SiliconFlow", "code": "siliconflow", "website": "https://siliconflow.cn", "description": "硅基流动，一站式大模型云服务平台", "api_base": "https://api.siliconflow.cn/v1", "api_docs_url": "https://docs.siliconflow.cn", "is_builtin": True, "is_active": True},
            {"name": "Groq", "code": "groq", "website": "https://groq.com", "description": "Groq 超低延迟推理平台", "api_base": "https://api.groq.com/openai/v1", "api_docs_url": "https://console.groq.com/docs", "is_builtin": True, "is_active": True},
            {"name": "自定义", "code": "custom", "website": "", "description": "自定义接入任意兼容 OpenAI API 的提供商", "api_base": "", "api_docs_url": "", "is_builtin": True, "is_active": True},
        ]

    @staticmethod
    def _get_builtin_models():
        return [
            {"model_id": "gpt-4o", "model_name": "GPT-4o", "provider_code": "openai", "category": "omni_modal", "description": "OpenAI 旗舰多模态模型", "context_window": 128000, "max_output_tokens": 16384, "pricing_input": 2.50, "pricing_output": 10.00, "supports_streaming": True, "supports_vision": True, "supports_function_calling": True, "supports_tools": True, "release_date": "2025-03-27", "sort_order": 1},
            {"model_id": "gpt-4o-mini", "model_name": "GPT-4o Mini", "provider_code": "openai", "category": "omni_modal", "description": "OpenAI 轻量级多模态模型", "context_window": 128000, "max_output_tokens": 16384, "pricing_input": 0.15, "pricing_output": 0.60, "supports_streaming": True, "supports_vision": True, "supports_function_calling": True, "supports_tools": True, "release_date": "2024-07-18", "sort_order": 2},
            {"model_id": "o1", "model_name": "o1", "provider_code": "openai", "category": "deep_thinking", "description": "OpenAI 深度推理模型", "context_window": 200000, "max_output_tokens": 100000, "pricing_input": 15.00, "pricing_output": 60.00, "supports_streaming": True, "supports_vision": True, "supports_function_calling": True, "supports_tools": True, "release_date": "2024-12-05", "sort_order": 3},
            {"model_id": "o1-mini", "model_name": "o1 Mini", "provider_code": "openai", "category": "deep_thinking", "description": "OpenAI 轻量推理模型", "context_window": 128000, "max_output_tokens": 65536, "pricing_input": 1.10, "pricing_output": 4.40, "supports_streaming": True, "supports_vision": False, "supports_function_calling": False, "supports_tools": False, "release_date": "2024-12-05", "sort_order": 4},
            {"model_id": "o3", "model_name": "o3", "provider_code": "openai", "category": "deep_thinking", "description": "OpenAI 最强推理模型", "context_window": 200000, "max_output_tokens": 100000, "pricing_input": 15.00, "pricing_output": 60.00, "supports_streaming": True, "supports_vision": True, "supports_function_calling": True, "supports_tools": True, "release_date": "2025-04-16", "sort_order": 5},
            {"model_id": "gpt-4-turbo", "model_name": "GPT-4 Turbo", "provider_code": "openai", "category": "text_generation", "description": "OpenAI 高性能文本生成模型", "context_window": 128000, "max_output_tokens": 4096, "pricing_input": 10.00, "pricing_output": 30.00, "supports_streaming": True, "supports_vision": True, "supports_function_calling": True, "supports_tools": True, "release_date": "2023-11-06", "sort_order": 6},
            {"model_id": "dall-e-3", "model_name": "DALL-E 3", "provider_code": "openai", "category": "image_generation", "description": "OpenAI 旗舰图片生成模型", "context_window": 0, "max_output_tokens": 0, "pricing_input": 0.04, "pricing_output": 0.0, "supports_streaming": False, "supports_vision": False, "supports_function_calling": False, "supports_tools": False, "release_date": "2023-11-06", "sort_order": 7},
            {"model_id": "whisper-1", "model_name": "Whisper", "provider_code": "openai", "category": "speech_recognition", "description": "OpenAI 通用语音识别模型", "context_window": 0, "max_output_tokens": 0, "pricing_input": 0.006, "pricing_output": 0.0, "supports_streaming": False, "supports_vision": False, "supports_function_calling": False, "supports_tools": False, "release_date": "2023-03-01", "sort_order": 8},
            {"model_id": "tts-1", "model_name": "TTS-1", "provider_code": "openai", "category": "speech_synthesis", "description": "OpenAI 标准语音合成模型", "context_window": 0, "max_output_tokens": 0, "pricing_input": 0.015, "pricing_output": 0.0, "supports_streaming": False, "supports_vision": False, "supports_function_calling": False, "supports_tools": False, "release_date": "2023-11-06", "sort_order": 9},
            {"model_id": "text-embedding-3-large", "model_name": "Text Embedding 3 Large", "provider_code": "openai", "category": "text_embedding", "description": "OpenAI 高性能文本向量模型", "context_window": 8191, "max_output_tokens": 0, "pricing_input": 0.13, "pricing_output": 0.0, "supports_streaming": False, "supports_vision": False, "supports_function_calling": False, "supports_tools": False, "release_date": "2024-01-25", "sort_order": 10},

            {"model_id": "gpt-4o-realtime-preview", "model_name": "GPT-4o Realtime", "provider_code": "openai", "category": "realtime_omni", "description": "OpenAI 实时多模态交互模型", "context_window": 128000, "max_output_tokens": 4096, "pricing_input": 5.00, "pricing_output": 20.00, "supports_streaming": True, "supports_vision": True, "supports_function_calling": True, "supports_tools": True, "release_date": "2024-12-17", "sort_order": 11},

            {"model_id": "gemini-2.5-pro", "model_name": "Gemini 2.5 Pro", "provider_code": "google", "category": "omni_modal", "description": "Google 最强多模态模型", "context_window": 1048576, "max_output_tokens": 65536, "pricing_input": 1.25, "pricing_output": 10.00, "supports_streaming": True, "supports_vision": True, "supports_function_calling": True, "supports_tools": True, "release_date": "2025-03-25", "sort_order": 20},
            {"model_id": "gemini-2.5-flash", "model_name": "Gemini 2.5 Flash", "provider_code": "google", "category": "omni_modal", "description": "Google 高速多模态模型", "context_window": 1048576, "max_output_tokens": 65536, "pricing_input": 0.15, "pricing_output": 0.60, "supports_streaming": True, "supports_vision": True, "supports_function_calling": True, "supports_tools": True, "release_date": "2025-03-25", "sort_order": 21},
            {"model_id": "gemini-2.0-flash", "model_name": "Gemini 2.0 Flash", "provider_code": "google", "category": "text_generation", "description": "Google 新一代高效模型", "context_window": 1048576, "max_output_tokens": 8192, "pricing_input": 0.10, "pricing_output": 0.40, "supports_streaming": True, "supports_vision": True, "supports_function_calling": True, "supports_tools": True, "release_date": "2024-12-11", "sort_order": 22},

            {"model_id": "claude-3.5-sonnet", "model_name": "Claude 3.5 Sonnet", "provider_code": "anthropic", "category": "text_generation", "description": "Anthropic 顶级文本生成模型", "context_window": 200000, "max_output_tokens": 8192, "pricing_input": 3.00, "pricing_output": 15.00, "supports_streaming": True, "supports_vision": True, "supports_function_calling": True, "supports_tools": True, "release_date": "2024-10-22", "sort_order": 30},
            {"model_id": "claude-3-opus", "model_name": "Claude 3 Opus", "provider_code": "anthropic", "category": "deep_thinking", "description": "Anthropic 最强分析模型", "context_window": 200000, "max_output_tokens": 4096, "pricing_input": 15.00, "pricing_output": 75.00, "supports_streaming": True, "supports_vision": True, "supports_function_calling": True, "supports_tools": True, "release_date": "2024-03-04", "sort_order": 31},
            {"model_id": "claude-3-haiku", "model_name": "Claude 3 Haiku", "provider_code": "anthropic", "category": "text_generation", "description": "Anthropic 极速轻量模型", "context_window": 200000, "max_output_tokens": 4096, "pricing_input": 0.25, "pricing_output": 1.25, "supports_streaming": True, "supports_vision": True, "supports_function_calling": True, "supports_tools": True, "release_date": "2024-03-13", "sort_order": 32},

            {"model_id": "deepseek-chat", "model_name": "DeepSeek Chat (V3)", "provider_code": "deepseek", "category": "text_generation", "description": "DeepSeek 通用对话模型 V3", "context_window": 131072, "max_output_tokens": 8192, "pricing_input": 0.27, "pricing_output": 1.10, "supports_streaming": True, "supports_vision": False, "supports_function_calling": True, "supports_tools": True, "release_date": "2025-03-24", "sort_order": 50},
            {"model_id": "deepseek-r1", "model_name": "DeepSeek R1", "provider_code": "deepseek", "category": "deep_thinking", "description": "DeepSeek 深度推理模型 R1", "context_window": 131072, "max_output_tokens": 8192, "pricing_input": 0.55, "pricing_output": 2.19, "supports_streaming": True, "supports_vision": False, "supports_function_calling": True, "supports_tools": True, "release_date": "2025-01-20", "sort_order": 51},

            {"model_id": "qwen-max", "model_name": "通义千问 Max", "provider_code": "alibaba", "category": "text_generation", "description": "阿里通义千问旗舰模型", "context_window": 131072, "max_output_tokens": 8192, "pricing_input": 2.80, "pricing_output": 11.20, "supports_streaming": True, "supports_vision": False, "supports_function_calling": True, "supports_tools": True, "release_date": "2025-01-28", "sort_order": 40},
            {"model_id": "qwen-plus", "model_name": "通义千问 Plus", "provider_code": "alibaba", "category": "text_generation", "description": "阿里通义千问增强版", "context_window": 131072, "max_output_tokens": 8192, "pricing_input": 0.80, "pricing_output": 3.20, "supports_streaming": True, "supports_vision": False, "supports_function_calling": True, "supports_tools": True, "release_date": "2025-01-28", "sort_order": 41},
            {"model_id": "qwq-32b", "model_name": "QwQ 32B", "provider_code": "alibaba", "category": "deep_thinking", "description": "阿里通义千问推理模型", "context_window": 131072, "max_output_tokens": 8192, "pricing_input": 0.55, "pricing_output": 2.19, "supports_streaming": True, "supports_vision": False, "supports_function_calling": False, "supports_tools": False, "release_date": "2025-03-05", "sort_order": 42},
            {"model_id": "qwen-vl-max", "model_name": "通义千问 VL Max", "provider_code": "alibaba", "category": "vision_understanding", "description": "阿里旗舰视觉理解模型", "context_window": 32768, "max_output_tokens": 4096, "pricing_input": 3.00, "pricing_output": 12.00, "supports_streaming": True, "supports_vision": True, "supports_function_calling": True, "supports_tools": True, "release_date": "2025-01-28", "sort_order": 43},

            {"model_id": "doubao-pro-32k", "model_name": "豆包 Pro 32K", "provider_code": "bytedance", "category": "text_generation", "description": "字节豆包旗舰模型", "context_window": 32768, "max_output_tokens": 8192, "pricing_input": 0.80, "pricing_output": 2.00, "supports_streaming": True, "supports_vision": False, "supports_function_calling": True, "supports_tools": True, "release_date": "2025-01-01", "sort_order": 45},

            {"model_id": "glm-4-plus", "model_name": "GLM-4 Plus", "provider_code": "zhipu", "category": "text_generation", "description": "智谱AI旗舰模型", "context_window": 131072, "max_output_tokens": 4096, "pricing_input": 0.80, "pricing_output": 2.00, "supports_streaming": True, "supports_vision": False, "supports_function_calling": True, "supports_tools": True, "release_date": "2025-02-18", "sort_order": 46},
            {"model_id": "glm-4v-plus", "model_name": "GLM-4V Plus", "provider_code": "zhipu", "category": "vision_understanding", "description": "智谱AI多模态视觉模型", "context_window": 16384, "max_output_tokens": 4096, "pricing_input": 1.20, "pricing_output": 3.00, "supports_streaming": True, "supports_vision": True, "supports_function_calling": True, "supports_tools": True, "release_date": "2025-02-18", "sort_order": 47},

            {"model_id": "moonshot-v1-8k", "model_name": "Moonshot V1 8K", "provider_code": "moonshot", "category": "text_generation", "description": "月之暗面 Kimi 标准模型", "context_window": 8192, "max_output_tokens": 4096, "pricing_input": 0.50, "pricing_output": 1.00, "supports_streaming": True, "supports_vision": False, "supports_function_calling": True, "supports_tools": True, "release_date": "2024-09-10", "sort_order": 48},

            {"model_id": "step-2-16k", "model_name": "Step-2 16K", "provider_code": "stepfun", "category": "omni_modal", "description": "阶跃星辰旗舰多模态模型", "context_window": 16384, "max_output_tokens": 4096, "pricing_input": 1.50, "pricing_output": 6.00, "supports_streaming": True, "supports_vision": True, "supports_function_calling": True, "supports_tools": True, "release_date": "2025-03-01", "sort_order": 49},

            {"model_id": "bge-m3", "model_name": "BGE-M3", "provider_code": "siliconflow", "category": "text_embedding", "description": "BAAI 多语言文本向量模型", "context_window": 8192, "max_output_tokens": 0, "pricing_input": 0.002, "pricing_output": 0.0, "supports_streaming": False, "supports_vision": False, "supports_function_calling": False, "supports_tools": False, "release_date": "2024-02-06", "sort_order": 52},

            {"model_id": "kling-v2.6", "model_name": "可灵 V2.6", "provider_code": "alibaba", "category": "video_generation", "description": "快手可灵视频生成模型", "context_window": 0, "max_output_tokens": 0, "pricing_input": 7.00, "pricing_output": 0.0, "supports_streaming": False, "supports_vision": False, "supports_function_calling": False, "supports_tools": False, "release_date": "2025-04-10", "sort_order": 53},

            {"model_id": "hailuo-02", "model_name": "海螺 AI 02", "provider_code": "minimax", "category": "video_generation", "description": "MiniMax 海螺视频生成模型", "context_window": 0, "max_output_tokens": 0, "pricing_input": 5.00, "pricing_output": 0.0, "supports_streaming": False, "supports_vision": False, "supports_function_calling": False, "supports_tools": False, "release_date": "2025-05-01", "sort_order": 54},

            {"model_id": "flux-1.1-pro", "model_name": "FLUX 1.1 Pro", "provider_code": "alibaba", "category": "image_generation", "description": "Black Forest Labs 顶级图片生成模型", "context_window": 0, "max_output_tokens": 0, "pricing_input": 0.04, "pricing_output": 0.0, "supports_streaming": False, "supports_vision": False, "supports_function_calling": False, "supports_tools": False, "release_date": "2024-12-10", "sort_order": 55},
        ]
