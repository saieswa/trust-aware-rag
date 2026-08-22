import pytest
from agents.retriever.agent import run_retriever_agent
from agents.critic.agent import run_critic_agent
from trust.trust_engine import compute_trust_report
from agents.pipeline.agent import run_full_pipeline


@pytest.mark.asyncio
async def test_research_paper_problem_statement_retrieval():
    """Verify that 'What is the problem statement of this paper?' returns relevant chunks."""
    query = "What is the problem statement of this paper?"
    state = run_retriever_agent(query, k=3)
    top_evidence = state.get("top_evidence", [])

    assert len(top_evidence) > 0
    top_chunk = top_evidence[0]
    # Check that score is solid and relevance is high
    assert top_chunk.get("final_rank_score", 0.0) >= 0.50
    assert any(
        term in top_chunk.get("text", "").lower()
        for term in ["redeep", "hallucination", "rag", "parametric", "external", "context", "table", "performance"]
    )


@pytest.mark.asyncio
async def test_research_paper_results_retrieval():
    """Verify that results queries retrieve Table / Experiments chunks."""
    query = "What are the main results?"
    state = run_retriever_agent(query, k=3)
    top_evidence = state.get("top_evidence", [])

    assert len(top_evidence) > 0
    top_chunk = top_evidence[0]
    assert top_chunk.get("final_rank_score", 0.0) >= 0.50


@pytest.mark.asyncio
async def test_honest_abstention_on_unrelated_query():
    """Verify that an off-topic query triggers honest abstention with low trust."""
    query = "What is the recipe for chocolate cake?"
    retriever_state = run_retriever_agent(query, k=3)
    top_ev = retriever_state.get("top_evidence", [])

    critic_state = run_critic_agent(query, top_ev)
    critic_report = critic_state.get("critic_report", {})

    trust_report = compute_trust_report(query, critic_report=critic_report)
    assert trust_report["trust_score"] < 0.50
    assert trust_report["decision"] == "abstain"

    pipeline_state = run_full_pipeline(query, trust_report)
    final_report = pipeline_state.get("final_report", {})
    assert "couldn't find sufficient verified evidence" in final_report.get("final_answer", "").lower() or "not reliable" in final_report.get("final_answer", "").lower()
