"""
Agent API routes with Document Scoping.
"""

from fastapi import APIRouter, Depends

from app.schemas.critic_agent import CriticAgentRequest, CriticAgentResponse
from app.schemas.retriever_agent import RetrieverAgentRequest, RetrieverAgentResponse
from app.schemas.synthesis import SynthesisRequest, SynthesisResponse
from app.services.critic_agent_service import CriticAgentService, get_critic_agent_service
from app.services.retriever_agent_service import RetrieverAgentService, get_retriever_agent_service
from app.services.synthesis_service import SynthesisService, get_synthesis_service

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.post(
    "/retriever/run",
    response_model=RetrieverAgentResponse,
    summary="Run the Retriever Agent",
)
async def retriever_run(
    request: RetrieverAgentRequest,
    service: RetrieverAgentService = Depends(get_retriever_agent_service),
) -> RetrieverAgentResponse:
    return await service.run(query=request.query, k=request.k, doc_id=getattr(request, "doc_id", None))


@router.post(
    "/critic/run",
    response_model=CriticAgentResponse,
    summary="Run the Critic Agent",
)
async def critic_run(
    request: CriticAgentRequest,
    service: CriticAgentService = Depends(get_critic_agent_service),
) -> CriticAgentResponse:
    return await service.run(
        query=request.query,
        k=request.k,
        evidence=request.evidence,
        doc_id=getattr(request, "doc_id", None),
    )


@router.post(
    "/synthesis/run",
    response_model=SynthesisResponse,
    summary="Run the Synthesizer + Verifier pipeline",
)
async def synthesis_run(
    request: SynthesisRequest,
    service: SynthesisService = Depends(get_synthesis_service),
) -> SynthesisResponse:
    return await service.run(
        query=request.query,
        k=request.k,
        max_retries=request.max_retries,
        trust_report=request.trust_report,
        doc_id=request.doc_id,
    )
