"""
Agent API routes.

- POST /agents/retriever/run — full LangGraph Retriever Agent (analyze ->
  decompose -> multi-search -> merge -> dedup -> rank -> top-k).
- POST /agents/critic/run    — full LangGraph Critic Agent (read evidence ->
  quality/reliability scoring -> contradiction detection -> support/
  contradict/neutral labeling -> structured report). Runs the Retriever
  Agent first automatically if the caller doesn't supply pre-fetched
  evidence.

Future agents (Synthesizer, Verifier) will be added the same way, under
the same /agents prefix.
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
    description=(
        "Analyzes the query, decomposes it into focused sub-queries if "
        "needed, searches the vector store once per sub-query, merges and "
        "deduplicates the results, ranks them (similarity + cross-query "
        "agreement), and returns the top-k evidence chunks."
    ),
)
async def retriever_run(
    request: RetrieverAgentRequest,
    service: RetrieverAgentService = Depends(get_retriever_agent_service),
) -> RetrieverAgentResponse:
    return service.run(query=request.query, k=request.k)


@router.post(
    "/critic/run",
    response_model=CriticAgentResponse,
    summary="Run the Critic Agent",
    description=(
        "Reads retrieved evidence, measures evidence quality and source "
        "reliability, detects contradictions between chunks, and labels "
        "each chunk as support/contradict/neutral relative to the question. "
        "If `evidence` is omitted from the request, runs the Retriever "
        "Agent first to fetch it."
    ),
)
async def critic_run(
    request: CriticAgentRequest,
    service: CriticAgentService = Depends(get_critic_agent_service),
) -> CriticAgentResponse:
    return service.run(query=request.query, k=request.k, evidence=request.evidence)


@router.post(
    "/synthesis/run",
    response_model=SynthesisResponse,
    summary="Run the Synthesizer + Verifier pipeline",
    description=(
        "Generates an answer using only 'support'-labeled evidence from the "
        "Critic Agent (via the Trust Score system), then verifies it "
        "sentence-by-sentence against that evidence. Rejected drafts are "
        "automatically retried (up to `max_retries`) with the Verifier's "
        "revision suggestions fed back into the next synthesis attempt. "
        "If `trust_report` is omitted, runs the full Retriever -> Critic -> "
        "Trust chain first."
    ),
)
async def synthesis_run(
    request: SynthesisRequest,
    service: SynthesisService = Depends(get_synthesis_service),
) -> SynthesisResponse:
    return service.run(
        query=request.query,
        k=request.k,
        max_retries=request.max_retries,
        trust_report=request.trust_report,
    )
