import { splitAnswerIntoParts } from "@/lib/utils";

interface AnswerTextProps {
  text: string;
  onCitationClick?: (chunkId: string) => void;
}

function cleanText(t: string): string {
  return t
    .replace(/\[doc_[a-zA-Z0-9_\-]+_chunk\d+\]/gi, "")
    .replace(/\[chunk_\d+\]/gi, "")
    .replace(/\s{2,}/g, " ");
}

export function AnswerText({ text, onCitationClick }: AnswerTextProps) {
  const lines = text.split("\n");

  const renderLine = (line: string, lineIdx: number) => {
    const trimmed = line.trim();
    if (!trimmed) {
      return <div key={lineIdx} className="h-2" />;
    }

    // Markdown Header 3 (### Heading)
    if (trimmed.startsWith("### ")) {
      const headingText = trimmed.replace(/^###\s+/, "");
      return (
        <h4
          key={lineIdx}
          className="mt-3 mb-1.5 font-semibold text-xs text-accent-phosphor tracking-wide uppercase font-mono flex items-center gap-1.5"
        >
          {cleanText(headingText)}
        </h4>
      );
    }

    // Markdown Header 2 (## Heading)
    if (trimmed.startsWith("## ")) {
      const headingText = trimmed.replace(/^##\s+/, "");
      return (
        <h3 key={lineIdx} className="mt-3 mb-1.5 font-semibold text-sm text-ink-primary font-mono">
          {cleanText(headingText)}
        </h3>
      );
    }

    // Numbered list items (1. Step)
    if (/^\d+\.\s+/.test(trimmed)) {
      const stepNum = trimmed.match(/^(\d+)\./)?.[1] || "•";
      const stepText = trimmed.replace(/^\d+\.\s+/, "");
      return (
        <div key={lineIdx} className="flex items-start gap-2 my-1 pl-1">
          <span className="flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-full bg-accent-phosphor/15 text-[10px] font-mono font-bold text-accent-phosphor mt-0.5">
            {stepNum}
          </span>
          <span className="text-sm leading-relaxed text-ink-primary/95">{cleanText(stepText)}</span>
        </div>
      );
    }

    // Bullet points (- Point or * Point or • Point)
    const isBullet = trimmed.startsWith("- ") || trimmed.startsWith("* ") || trimmed.startsWith("• ");
    const content = isBullet ? trimmed.replace(/^[-*•]\s+/, "") : line;
    const parts = splitAnswerIntoParts(content);

    return (
      <div
        key={lineIdx}
        className={`text-sm leading-relaxed text-ink-primary/95 ${
          isBullet ? "flex items-start gap-2 my-1 pl-2" : "my-1"
        }`}
      >
        {isBullet && <span className="text-accent-phosphor font-bold mt-0.5">•</span>}
        <div className="flex-1 flex-wrap">
          {parts.map((part, i) =>
            part.type === "text" ? (
              <span key={i}>{cleanText(part.value)}</span>
            ) : (
              <button
                key={i}
                type="button"
                onClick={() => onCitationClick?.(part.value)}
                className="mx-0.5 inline-flex items-center rounded border border-accent-phosphor/40 bg-accent-phosphor/10 px-1.5 py-0.2 font-mono text-[11px] font-medium text-accent-phosphor hover:bg-accent-phosphor/20 transition-colors align-middle"
                title={`View evidence chunk ${part.value}`}
              >
                [Citation]
              </button>
            )
          )}
        </div>
      </div>
    );
  };

  return <div className="flex flex-col">{lines.map(renderLine)}</div>;
}
