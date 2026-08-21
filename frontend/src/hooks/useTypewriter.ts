"use client";

import { useEffect, useState } from "react";

/**
 * Reveals `text` a chunk at a time on a short interval, purely a visual
 * effect once the full answer has already arrived from the backend (see
 * useChat.ts's docstring — there is no real token stream to consume yet).
 * Revealing by whole words rather than characters keeps citation markers
 * like "[doc_a1b2_chunk0]" intact instead of animating through unreadable
 * partial brackets.
 */
export function useTypewriter(text: string, wordsPerTick = 3, tickMs = 24): string {
  const [visibleWordCount, setVisibleWordCount] = useState(0);

  useEffect(() => {
    setVisibleWordCount(0);
    if (!text) return;

    const words = text.split(" ");
    if (words.length === 0) return;

    const interval = setInterval(() => {
      setVisibleWordCount((count) => {
        const next = count + wordsPerTick;
        if (next >= words.length) {
          clearInterval(interval);
          return words.length;
        }
        return next;
      });
    }, tickMs);

    return () => clearInterval(interval);
  }, [text, wordsPerTick, tickMs]);

  return text.split(" ").slice(0, visibleWordCount).join(" ");
}
