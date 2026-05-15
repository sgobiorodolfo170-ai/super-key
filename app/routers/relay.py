import json
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse

from app.middleware.auth import verify_api_token
from app.services.relay_service import RelayService
from app.services.distributor import Distributor
from app.services.channel_service import ChannelService
from app.services.custom_model_service import CustomModelService
from app.models.model_classification import ModelClassification
from app.models.custom_model import CustomModel
from app.database import async_session
from sqlalchemy import select

router = APIRouter(prefix="/v1", dependencies=[Depends(verify_api_token)])

MODEL_CATEGORIES = [
    "omni_modal", "deep_thinking", "text_generation", "vision_understanding",
    "video_generation", "image_generation", "3d_generation",
    "speech_recognition", "speech_synthesis",
    "multimodal_embedding", "text_embedding",
    "realtime_omni", "realtime_speech_synthesis",
    "realtime_speech_recognition", "realtime_speech_translation",
]

CATEGORY_LABELS = {
    "omni_modal": "全模态",
    "deep_thinking": "深度思考",
    "text_generation": "文本生成",
    "vision_understanding": "视觉理解",
    "video_generation": "视频生成",
    "image_generation": "图片生成",
    "3d_generation": "3D生成",
    "speech_recognition": "语音识别",
    "speech_synthesis": "语音合成",
    "multimodal_embedding": "多模态向量",
    "text_embedding": "文本向量",
    "realtime_omni": "实时全模态",
    "realtime_speech_synthesis": "实时语音合成",
    "realtime_speech_recognition": "实时语音识别",
    "realtime_speech_translation": "实时语音翻译",
}


@router.post("/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    return await RelayService.relay_chat(request, body)


@router.get("/models")
async def list_models(request: Request):
    allowed_models = getattr(request.state, "allowed_models", [])

    async with async_session() as session:
        result = await session.execute(select(ModelClassification).order_by(ModelClassification.sort_order))
        models = result.scalars().all()

        custom_result = await session.execute(select(CustomModel).where(CustomModel.is_active == True))
        custom_models = custom_result.scalars().all()

        data = []

        for m in models:
            if allowed_models and m.model_id not in allowed_models:
                continue
            data.append({
                "id": m.model_id,
                "object": "model",
                "created": 0,
                "owned_by": m.provider_code,
                "type": "builtin",
            })

        for cm in custom_models:
            if allowed_models and cm.model_id not in allowed_models:
                continue
            data.append({
                "id": cm.model_id,
                "object": "model",
                "created": 0,
                "owned_by": "custom",
                "type": "custom",
                "name": cm.name,
            })

        return {"object": "list", "data": data}


@router.get("/models/categories")
async def list_categories():
    async with async_session() as session:
        from sqlalchemy import func
        stmt = (
            select(
                ModelClassification.category,
                func.count(ModelClassification.id).label("cnt"),
                func.json_group_array(
                    func.json_object(
                        "id", ModelClassification.model_id,
                        "name", ModelClassification.model_name,
                        "provider_code", ModelClassification.provider_code,
                    )
                ).label("models_json"),
            )
            .where(ModelClassification.category.in_(MODEL_CATEGORIES))
            .group_by(ModelClassification.category)
        )
        result = await session.execute(stmt)
        rows = result.all()

        result_data = []
        cat_data = {}
        for row in rows:
            cat_data[row.category] = {
                "count": row.cnt,
                "models_json": row.models_json,
            }

        for cat in MODEL_CATEGORIES:
            info = cat_data.get(cat)
            if info:
                import json
                models_parsed = json.loads(info["models_json"])[:10]
                result_data.append({
                    "id": cat,
                    "name": CATEGORY_LABELS.get(cat, cat),
                    "model_count": info["count"],
                    "models": models_parsed,
                })
            else:
                result_data.append({
                    "id": cat,
                    "name": CATEGORY_LABELS.get(cat, cat),
                    "model_count": 0,
                    "models": [],
                })
    return {"data": result_data}


@router.get("/models/{model_id}")
async def get_model(model_id: str):
    async with async_session() as session:
        result = await session.execute(select(ModelClassification).where(ModelClassification.model_id == model_id))
        model = result.scalar_one_or_none()
        if not model:
            return JSONResponse({"error": {"message": f"Model not found: {model_id}"}}, status_code=404)
        return {
            "id": model.model_id,
            "object": "model",
            "created": 0,
            "owned_by": model.provider_code,
            "name": model.model_name,
            "category": model.category,
            "category_label": CATEGORY_LABELS.get(model.category, model.category),
            "description": model.description,
            "context_window": model.context_window,
            "max_output_tokens": model.max_output_tokens,
        }


@router.post("/images/generations")
async def image_generations(request: Request):
    return JSONResponse({"error": {"message": "Image generation via relay not yet implemented"}}, status_code=501)


@router.post("/embeddings")
async def embeddings(request: Request):
    return JSONResponse({"error": {"message": "Embedding via relay not yet implemented"}}, status_code=501)


@router.post("/audio/speech")
async def audio_speech(request: Request):
    return JSONResponse({"error": {"message": "Audio speech via relay not yet implemented"}}, status_code=501)


@router.post("/audio/transcriptions")
async def audio_transcriptions(request: Request):
    return JSONResponse({"error": {"message": "Audio transcription via relay not yet implemented"}}, status_code=501)
