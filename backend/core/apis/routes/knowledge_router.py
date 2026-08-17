from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from commons.dependencies import get_actor_id, get_organization_id, require_roles
from core.apis.schemas.assistant import KnowledgeDocumentResource, KnowledgeSearchRequest, KnowledgeSearchResponse, SourceCitation
from core.config import settings
from core.controllers import knowledge_controller

router = APIRouter()


def _resource(item: dict) -> KnowledgeDocumentResource:
    return KnowledgeDocumentResource(id=item["_id"], filename=item["filename"], content_type=item["content_type"],
                                     character_count=item["character_count"], chunk_count=item["chunk_count"], created_at=item["created_at"])


@router.get("/documents", response_model=list[KnowledgeDocumentResource], dependencies=[Depends(require_roles("viewer", "operator", "manager", "admin"))])
async def documents(organization_id: str = Depends(get_organization_id)):
    return [_resource(item) for item in await knowledge_controller.list_documents(organization_id)]


@router.post("/documents", response_model=KnowledgeDocumentResource, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("manager", "admin"))])
async def upload_document(file: UploadFile = File(...), organization_id: str = Depends(get_organization_id), actor_id: str = Depends(get_actor_id)):
    content = await file.read(settings.knowledge_max_file_bytes + 1)
    await file.close()
    if len(content) > settings.knowledge_max_file_bytes:
        raise HTTPException(status_code=413, detail=f"Document exceeds {settings.knowledge_max_file_bytes} bytes")
    try:
        return _resource(await knowledge_controller.ingest_document(organization_id, actor_id, file.filename or "document", file.content_type or "application/octet-stream", content))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles("manager", "admin"))])
async def delete_document(document_id: str, organization_id: str = Depends(get_organization_id)):
    if not await knowledge_controller.delete_document(organization_id, document_id):
        raise HTTPException(status_code=404, detail="Knowledge document not found")


@router.post("/search", response_model=KnowledgeSearchResponse, dependencies=[Depends(require_roles("viewer", "operator", "manager", "admin"))])
async def search(payload: KnowledgeSearchRequest, organization_id: str = Depends(get_organization_id)):
    chunks = await knowledge_controller.search(organization_id, payload.query, payload.top_k)
    return KnowledgeSearchResponse(sources=[SourceCitation(document_id=item["document_id"], filename=item["filename"], chunk_index=item["chunk_index"], excerpt=item["text"][:280], score=item["score"]) for item in chunks])
