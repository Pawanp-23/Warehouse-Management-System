from fastapi import APIRouter, Depends

from commons.dependencies import get_organization_id, require_roles
from core.apis.schemas.assistant import AssistantChatRequest, AssistantChatResponse
from core.controllers import assistant_controller

router = APIRouter()


@router.post("/chat", response_model=AssistantChatResponse, dependencies=[Depends(require_roles("viewer", "operator", "manager", "admin"))])
async def chat(payload: AssistantChatRequest, organization_id: str = Depends(get_organization_id)):
    return await assistant_controller.chat(organization_id, payload.message, payload.history)
