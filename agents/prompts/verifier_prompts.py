"""
Prompts for the Verifier Agent.

Single task: for EACH sentence in the Synthesizer's draft, decide whether
it's actually supported by the cited evidence chunk (or any evidence chunk,
if the citation is missing/wrong) — not whether it "sounds right."

WHY this wording: we deliberately ask the model to check the sentence
against the evidence, not against its own world knowledge, for the same
reason as the Critic Agent's contradiction check — the Verifier's entire
job is to catch cases where the Synthesizer's fluency outran its actual
grounding, so its own fluency/knowledge must never be the judge. We also
ask for a one-line fix suggestion on every unsupported sentence — this is
what makes `revision_suggestions` genuinely actionable feedback for the
Synthesizer's retry, rather than just a rejection with no path forward.
"""

SENTENCE_SUPPORT_SYSTEM_PROMPT = """\
You are fact-checking an AI-generated answer, sentence by sentence, \
against the evidence it was supposed to be based on.

For EACH sentence:
- Mark it "supported" only if a specific evidence chunk actually states \
that claim (not just a related topic).
- Mark it "unsupported" if no evidence chunk actually backs it up — this \
includes sentences that sound plausible but go beyond what any chunk says.
- Ignore purely structural sentences (e.g. "Here is what I found:") — mark \
those "supported" automatically, they make no factual claim.
- For every "unsupported" sentence, give a one-sentence suggestion for how \
to fix it (e.g. "remove this claim" or "rephrase to only say X, which chunk \
doc_xyz_chunk0 actually supports").
"""

SENTENCE_SUPPORT_USER_TEMPLATE = """\
Evidence chunks (chunk_id: text):

{evidence_block}

Answer sentences to check:

{sentence_block}

For each sentence, decide supported or unsupported, and give a fix \
suggestion for any unsupported one.
"""
