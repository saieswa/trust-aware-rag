import pytest
from agents.retriever.agent import run_retriever_agent
from agents.critic.agent import run_critic_agent
from trust.trust_engine import compute_trust_report
from agents.pipeline.agent import run_full_pipeline
from retrieval.retriever import get_retrieval_pipeline
from retrieval.loaders.document_loader import Document


@pytest.mark.asyncio
async def test_document_scoping_and_switching():
    pipeline = get_retrieval_pipeline()

    # Create Document A: ReDeEP Paper
    doc_a = Document(
        doc_id="doc_paper_a",
        title="ReDeEP: Detecting Hallucination in Retrieval Augmented Generation",
        source_path="paper_a.pdf",
        content=(
            "ReDeEP: Detecting Hallucination in Retrieval Augmented Generation via Mechanistic Interpretability\n\n"
            "Abstract\n"
            "Retrieval-Augmented Generation (RAG) models can produce hallucinations by generating outputs that conflict with the retrieved information. "
            "Detecting such hallucinations requires disentangling how Large Language Models (LLMs) utilize external and parametric knowledge. "
            "We propose ReDeEP to detect RAG hallucinations using mechanistic interpretability."
        ),
        metadata={"file_type": "pdf", "page_number": 1, "section": "Abstract"},
    )

    # Create Document B: Clinical Guideline
    doc_b = Document(
        doc_id="doc_paper_b",
        title="Clinical Guideline Summary: Drug X and Drug Y Interaction (2025 Revision)",
        source_path="paper_b.pdf",
        content=(
            "Clinical Guideline Summary: Drug X and Drug Y Interaction (2025 Revision)\n\n"
            "Concurrent use of Drug X and Drug Y is not recommended. Clinical studies have shown a significant increase in adverse cardiac events "
            "when both agents are administered simultaneously. Patients currently taking Drug X should discontinue the medication under physician supervision."
        ),
        metadata={"file_type": "pdf", "page_number": 1, "section": "Guideline"},
    )

    pipeline.index_document(doc_a)
    pipeline.index_document(doc_b)

    # -------------------------------------------------------------
    # TEST 1: Query Document A with doc_id="doc_paper_a"
    # -------------------------------------------------------------
    query_title = "What is the title of this paper?"
    retriever_state_a = run_retriever_agent(query_title, k=3, doc_id="doc_paper_a")
    top_ev_a = retriever_state_a.get("top_evidence", [])

    assert len(top_ev_a) > 0
    # Strict isolation: 100% of chunks must belong to doc_paper_a
    for chunk in top_ev_a:
        assert chunk["doc_id"] == "doc_paper_a"
        assert "drug" not in chunk["text"].lower()

    trust_a = compute_trust_report(query_title, critic_report=run_critic_agent(query_title, top_ev_a)["critic_report"], doc_id="doc_paper_a")
    res_a = run_full_pipeline(query_title, trust_a, doc_id="doc_paper_a")["final_report"]
    assert "redeep" in res_a["final_answer"].lower()

    # -------------------------------------------------------------
    # TEST 2: Query Document B with doc_id="doc_paper_b"
    # -------------------------------------------------------------
    retriever_state_b = run_retriever_agent(query_title, k=3, doc_id="doc_paper_b")
    top_ev_b = retriever_state_b.get("top_evidence", [])

    assert len(top_ev_b) > 0
    # Strict isolation: 100% of chunks must belong to doc_paper_b
    for chunk in top_ev_b:
        assert chunk["doc_id"] == "doc_paper_b"
        assert "redeep" not in chunk["text"].lower()

    trust_b = compute_trust_report(query_title, critic_report=run_critic_agent(query_title, top_ev_b)["critic_report"], doc_id="doc_paper_b")
    res_b = run_full_pipeline(query_title, trust_b, doc_id="doc_paper_b")["final_report"]
    assert "clinical guideline" in res_b["final_answer"].lower() or "drug x" in res_b["final_answer"].lower()

    # -------------------------------------------------------------
    # TEST 3: DOCUMENT-LEVEL Query: "Can you explain this PDF?" on Document A
    # -------------------------------------------------------------
    query_doc_level = "Can you explain this PDF?"
    retriever_state_dl = run_retriever_agent(query_doc_level, k=5, doc_id="doc_paper_a")
    top_ev_dl = retriever_state_dl.get("top_evidence", [])

    assert len(top_ev_dl) > 0
    for chunk in top_ev_dl:
        assert chunk["doc_id"] == "doc_paper_a"
        assert "drug" not in chunk["text"].lower()

    trust_dl = compute_trust_report(query_doc_level, critic_report=run_critic_agent(query_doc_level, top_ev_dl)["critic_report"], doc_id="doc_paper_a")
    # Must NOT abstain for document-level questions on an indexed document
    assert trust_dl["trust_score"] >= 0.50
    assert trust_dl["decision"] != "abstain"

    res_dl = run_full_pipeline(query_doc_level, trust_dl, doc_id="doc_paper_a")["final_report"]
    assert "redeep" in res_dl["final_answer"].lower() or "document overview" in res_dl["final_answer"].lower() or "rag" in res_dl["final_answer"].lower()

    # -------------------------------------------------------------
    # TEST 4: Query Problem Statement on Document B
    # -------------------------------------------------------------
    query_problem = "What is the problem statement?"
    retriever_state_b2 = run_retriever_agent(query_problem, k=3, doc_id="doc_paper_b")
    top_ev_b2 = retriever_state_b2.get("top_evidence", [])

    for chunk in top_ev_b2:
        assert chunk["doc_id"] == "doc_paper_b"
        assert "redeep" not in chunk["text"].lower()

    # -------------------------------------------------------------
    # TEST 5: Switch Back to Document A
    # -------------------------------------------------------------
    retriever_state_a2 = run_retriever_agent(query_title, k=3, doc_id="doc_paper_a")
    top_ev_a2 = retriever_state_a2.get("top_evidence", [])

    assert len(top_ev_a2) > 0
    for chunk in top_ev_a2:
        assert chunk["doc_id"] == "doc_paper_a"
        assert "drug" not in chunk["text"].lower()

    # -------------------------------------------------------------
    # TEST 6: Off-Topic / Math Question: "What is 2 + 2?"
    # -------------------------------------------------------------
    query_math = "What is 2 + 2?"
    retriever_state_math = run_retriever_agent(query_math, k=3, doc_id="doc_paper_a")
    top_ev_math = retriever_state_math.get("top_evidence", [])

    critic_math = run_critic_agent(query_math, top_ev_math)
    trust_math = compute_trust_report(query_math, critic_report=critic_math["critic_report"], doc_id="doc_paper_a")

    assert trust_math["trust_score"] < 0.50
    assert trust_math["decision"] == "abstain"

    res_math = run_full_pipeline(query_math, trust_math, doc_id="doc_paper_a")["final_report"]
    assert "cannot be answered" in res_math["final_answer"].lower() or "insufficient" in res_math["final_answer"].lower() or "couldn't find" in res_math["final_answer"].lower()
    # Must NOT have unresolved template placeholder {reason}
    assert "{reason}" not in res_math["final_answer"]
