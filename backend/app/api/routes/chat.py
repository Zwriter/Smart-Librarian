from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_chat_service
from app.domain.chat_request import ChatRequest
from app.domain.chat_response import ChatResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(
	request: ChatRequest,
	service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResponse:
	return service.recommend(request)