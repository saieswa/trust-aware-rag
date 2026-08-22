"use client";

import { useCallback, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { ChatTurn, PipelineStage } from "@/types/api";

const STAGE_SEQUENCE: PipelineStage[] = ["retrieving", "critiquing", "scoring", "synthesizing", "verifying"];
export const STAGE_LABELS: Record<PipelineStage, string> = {
  retrieving: "Retrieving document evidence",
  critiquing: "Checking evidence quality",
  scoring: "Computing trust score",
  synthesizing: "Drafting grounded answer",
  verifying: "Verifying against source citations",
  done: "Done",
};

function uid(): string {
  return Math.random().toString(36).slice(2, 10);
}

export function useChat(activeDocId?: string) {
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
        const result = await api.runSynthesis(query, 5, 2, activeDocId);
        clearStageTimers();
        updateTurn(id, { status: "done", stage: "done", result });
      } catch (error) {
        clearStageTimers();
        const message = error instanceof ApiError ? error.message : "Something went wrong.";
        updateTurn(id, { status: "error", errorMessage: message });
      }
    },
    [activeDocId, simulateStages, updateTurn]
  );

  const retryTurn = useCallback(
    (id: string) => {
      const turn = turns.find((t) => t.id === id);
      if (!turn) return;
      updateTurn(id, { status: "pending", stage: "retrieving", errorMessage: undefined });
      simulateStages(id);
      api
        .runSynthesis(turn.query, 5, 2, activeDocId)
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
    [activeDocId, turns, simulateStages, updateTurn]
  );

  const clearChat = useCallback(() => {
    clearStageTimers();
    setTurns([]);
  }, []);

  return { turns, submitQuery, retryTurn, clearChat };
}
