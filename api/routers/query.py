from fastapi import APIRouter

from api.database import GetDB
from api.schemas.query import QueryRequest, QueryResponse
from api.services.query_service import query_documents

router = APIRouter(tags=["Query"])


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest, db: GetDB) -> QueryResponse:
    return await query_documents(db, request.question)
