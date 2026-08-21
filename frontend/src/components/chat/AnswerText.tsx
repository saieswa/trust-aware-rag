import { splitAnswerIntoParts } from "@/lib/utils";

/**
 * Renders the Synthesizer's raw answer text, turning every inline
 * [chunk_id] citation marker into a small clickable-looking chip rather
 * than leaving raw brackets in the prose — this is what makes "every
 * claim cites its evidence" visible and legible rather than a fact you
 * have to take on faith.
 */
export function AnswerText({ text, onCitationClick }: { text: string; onCitationClick?: (chunkId: string) => void }) {
  const parts = splitAnswerIntoParts(text);

  return (
    <p className="text-sm leading-relaxed text-ink-primary">
      {parts.map((part, i) =>
        part.type === "text" ? (
          <span key={i}>{part.value}</span>
        ) : (
          <button
            key={i}
            onClick={() => onCitationClick?.(part.value)}
            className="mx-0.5 inline-flex items-center rounded border border-accent-phosphor/40 bg-accent-phosphor/10 px-1.5 py-0.5 font-mono text-[11px] text-accent-phosphor hover:bg-accent-phosphor/20 transition-colors align-middle"
            title={`View evidence chunk ${part.value}`}
          >
            {part.value}
          </button>
        )
      )}
    </p>
  );
}
