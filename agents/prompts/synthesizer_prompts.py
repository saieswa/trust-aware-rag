"""
Prompts for the Synthesizer Agent.

One prompt, used on both the first attempt and any retry — the retry case
simply has `revision_feedback` filled in instead of being empty.

WHY this wording: the system prompt's most important line is "Do not use
any knowledge you have outside of the evidence provided" — this is the
single instruction that turns a general-purpose LLM into a grounded
synthesizer. Without it, the model will happily fill small gaps with its
own training knowledge, which is exactly the hallucination risk this whole
project exists to prevent. We also require inline citations
(`[chunk_id]`) on every factual sentence — this is what lets the Verifier
Agent (next stage) check each sentence against a specific, named piece of
evidence instead of the evidence set as a vague whole.

The explicit permission to write "The available evidence does not fully
answer this question" is equally important: without being told that's an
acceptable output, models are biased toward always producing a confident,
complete-sounding answer even from thin evidence.
"""

SYNTHESIS_SYSTEM_PROMPT = """\
You are writing an answer using ONLY the evidence chunks provided below — \
never your own outside knowledge.

Rules:
- Every factual sentence must be directly supported by at least one \
evidence chunk, and must end with a citation to that chunk's id in \
square brackets, e.g. [doc_a1b2c3d4_chunk0].
- Do not combine two chunks into a claim neither one makes on its own.
- If the evidence only partially answers the question, say what it does \
answer and explicitly note what it doesn't cover — do not fill the gap \
with your own knowledge.
- If the evidence doesn't meaningfully answer the question at all, say so \
plainly instead of writing a confident-sounding answer anyway.
- Keep the answer concise — a few sentences, not an essay.
"""

SYNTHESIS_USER_TEMPLATE = """\
Original question: {query}

Evidence chunks (chunk_id: text):

{evidence_block}
{revision_block}
Write the answer now, following the rules above.
"""

REVISION_FEEDBACK_TEMPLATE = """
Your previous answer was rejected by a fact-checker for these reasons:
{feedback}

Write a new answer that fixes these issues — remove or rephrase any claim \
that isn't directly supported by a specific evidence chunk.
"""
