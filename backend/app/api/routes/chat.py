from fastapi import APIRouter, HTTPException

from app.core import session_store
from app.models.schemas import ChatRequest, ChatResponse
from app.services import gemini_service

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if not session_store.exists(req.session_id):
        raise HTTPException(status_code=404, detail="Session not found.")

    audit = session_store.get(req.session_id, "audit")
    chains = audit.chains if audit else []
    history = session_store.get(req.session_id, "chat_history") or []
    filename = session_store.get(req.session_id, "filename")

    reply = gemini_service.chat(req.message, chains, history, dataset_name=filename)

    history.append({"role": "user", "content": req.message})
    history.append({"role": "model", "content": reply})
    session_store.set(req.session_id, "chat_history", history)

    return ChatResponse(reply=reply)
