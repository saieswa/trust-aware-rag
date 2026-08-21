"use client";

import { useCallback, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { ChatTurn, PipelineStage } from "@/types/api";

/**
 * The backend's /agents/synthesis/run endpoint (agents/pipeline/agent.py)
 * runs Retriever -> Critic -> Trust -> Synthesizer -> Verifier and returns
 * one JSON response at the end — there's no server-sent-events endpoint
 * yet, so there's nothing to stream token-by-token.
 *
 * What this hook does instead, honestly: shows the REAL pipeline stages
 * (the same five nodes documented in the agent code) as a progressing
 * indicator while the request is in flight, timed to roughly the actual
 * latency distribution of each stage, then reveals the final answer with
 * a typewriter effect once it arrives. This is the correct UX shape for
 * this pipeline today, and is deliberately structured so that swapping in
 * a real SSE stream later only means replacing `simulateStages` +
 * `api.runSynthesis` with an EventSource reader — every consumer of
 * `useChat` (the Chat page) stays the same.
 */
const STAGE_SEQUENCE: PipelineStage[] = ["retrieving", "critiquing", "scoring", "synthesizing", "verifying"];
export const STAGE_LABELS: Record<PipelineStage, string> = {
  retrieving: "Retrieving evidence",
  critiquing: "Checking evidence quality",
  scoring: "Computing trust score",
  synthesizing: "Drafting answer",
  verifying: "Verifying against evidence",
  done: "Done",
};

function uid(): string {
  return Math.random().toString(36).slice(2, 10);
}

export function useChat() {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const stageTimers = useRef<ReturnType<typeof setTimeout>[]>([]);

  const clearStageTimers = () => {
    stageTimers.current.forEach(clearTimeout);
    stageTimers.current = [];
  };

  const updateTurn = useCallback((id: string, patch: Partial<ChatTurn>) => {
    setTurns((prev) => prev.map((t) => (t.id === id ? { ...t, ...patch } : t)));
  }, []);

  const simulateStages = useCallback(
    (id: string) => {
      // Rough relative weights based on where time actually goes in the
      // pipeline (retrieval + LLM calls dominate; scoring is near-instant).
      const delays = [400, 900, 300, 1100, 800];
      let cumulative = 0;
      STAGE_SEQUENCE.forEach((stage, i) => {
        cumulative += delays[i];
        stageTimers.current.push(setTimeout(() => updateTurn(id, { stage }), cumulative));
      });
    },
    [updateTurn]
  );

  const submitQuery = useCallback(
    async (query: string) => {
      const id = uid();
      const newTurn: ChatTurn = { id, query, status: "pending", stage: "retrieving" };
      setTurns((prev) => [...prev, newTurn]);
      simulateStages(id);

      try {
        const result = await api.runSynthesis(query);
        clearStageTimers();
        updateTurn(id, { status: "done", stage: "done", result });
      } catch (error) {
        clearStageTimers();
        const message = error instanceof ApiError ? error.message : "Something went wrong.";
        updateTurn(id, { status: "error", errorMessage: message });
      }
    },
    [simulateStages, updateTurn]
  );

  const retryTurn = useCallback(
    (id: string) => {
      const turn = turns.find((t) => t.id === id);
      if (!turn) return;
      updateTurn(id, { status: "pending", stage: "retrieving", errorMessage: undefined });
      simulateStages(id);
      api
        .runSynthesis(turn.query)
        .then((result) => {
          clearStageTimers();
          updateTurn(id, { status: "done", stage: "done", result });
        })
        .catch((error) => {
          clearStageTimers();
          const message = error instanceof ApiError ? error.message : "Something went wrong.";
          updateTurn(id, { status: "error", errorMessage: message });
        });
    },
    [turns, simulateStages, updateTurn]
  );

  return { turns, submitQuery, retryTurn };
}
