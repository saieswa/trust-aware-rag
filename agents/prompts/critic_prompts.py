"""
Prompts for the Critic Agent.

Two separate LLM tasks, two separate prompts — deliberately not combined
into one mega-prompt, because they ask the model to do two different kinds
of reasoning:

1. CONTRADICTION_DETECTION — compares evidence chunks *against each other*
   to find factual disagreements, independent of the original question.
   This is a symmetric, pairwise comparison task.

2. EVIDENCE_LABELING — judges each chunk *against the original question*
   (does it help answer it, conflict with better evidence, or say nothing
   relevant?). This is a per-chunk classification task that also needs to
   know which chunks were already flagged as contradicting one another
   (output of task 1), so a low-quality chunk that contradicts a
   high-quality one can correctly be labeled "contradict" rather than
   "support".

Splitting them keeps each prompt focused and each output easy to validate,
and it means the two stages can be swapped, tuned, or evaluated
independently later.
"""

# ============================================================
# Prompt 1 — Contradiction Detection
# ============================================================
#
# WHY this wording: we explicitly tell the model to compare evidence
# *against other evidence*, not against outside knowledge — the model's
# own training data must never be used to judge "correctness," only
# whether the provided chunks actually agree or disagree with each other.
# This keeps the Critic Agent's judgments grounded in the retrieved
# evidence, consistent with the whole project's goal of auditable,
# evidence-based trust — not the model's opinion.
#
# We also explicitly ask it to ignore chunks that are simply about
# different sub-topics (e.g. "shipping costs" vs "refund policy" chunks
# aren't a "contradiction," they're just unrelated) — without this
# instruction, models tend to over-flag loosely related chunks as
# contradictory.

CONTRADICTION_DETECTION_SYSTEM_PROMPT = """\
You are a fact-checking assistant comparing pieces of retrieved evidence \
against EACH OTHER — not against your own knowledge.

Your only job: find pairs of evidence chunks that make factually \
conflicting claims about the same specific topic (e.g. one says a refund \
window is 30 days, another says 14 days for the same policy).

Rules:
- Only flag a pair if they discuss the SAME specific fact and disagree on it.
- Do NOT flag two chunks as contradictory just because they cover \
different topics or sub-topics.
- Do NOT use any outside knowledge of your own to judge which one is \
correct — only report that they disagree, and briefly state what they \
each claim.
- If there are no contradictions, return an empty list.
"""

CONTRADICTION_DETECTION_USER_TEMPLATE = """\
Evidence chunks (chunk_id: text):

{evidence_block}

List every pair of chunk_ids that factually contradict each other, with a \
short explanation of what each side claims.
"""


# ============================================================
# Prompt 2 — Evidence Labeling (Support / Contradict / Neutral)
# ============================================================
#
# WHY this wording: this prompt deliberately anchors the label to the
# ORIGINAL QUESTION, not to "is this chunk true." A chunk can be entirely
# accurate on its own and still be "neutral" if it doesn't bear on the
# question asked. And a chunk that IS relevant but was already flagged
# (by Prompt 1) as contradicting a more reliable chunk should be labeled
# "contradict," so the Synthesizer Agent (next step) knows not to treat
# it as usable support.
#
# We feed the known contradiction pairs from Prompt 1 directly into this
# prompt so the model doesn't have to re-derive them — each stage does one
# job and hands its output forward, exactly like the Retriever Agent's
# node design.

EVIDENCE_LABELING_SYSTEM_PROMPT = """\
You are judging how each piece of evidence relates to a user's question.

For EACH evidence chunk, assign exactly one label:
- "support"    — the chunk provides evidence that helps answer the question, \
and is not contradicted by more reliable evidence.
- "contradict" — the chunk's claim conflicts with another, more reliable \
piece of evidence (you will be told which chunks already conflict).
- "neutral"    — the chunk is not clearly relevant to the question, or \
takes no real stance on it.

Use the provided list of known contradicting chunk pairs to help decide \
"support" vs "contradict": between two conflicting chunks, the one that \
looks more authoritative, specific, or current should be "support" and \
the other should be "contradict".
"""

EVIDENCE_LABELING_USER_TEMPLATE = """\
Original question: {query}

Evidence chunks (chunk_id: text):

{evidence_block}

Known contradicting pairs (from a previous fact-check step):
{contradiction_block}

Label every chunk_id as support, contradict, or neutral, with a short reason.
"""
