import { splitAnswerIntoParts } from "@/lib/utils";

interface AnswerTextProps {
  text: string;
  onCitationClick?: (chunkId: string) => void;
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
          className="mt-3 mb-1.5 font-semibold text-xs text-ink-primary flex items-center gap-1.5 text-accent-phosphor tracking-wide uppercase font-mono"
        >
          {headingText}
        </h4>
      );
    }

    // Markdown Header 2 (## Heading)
    if (trimmed.startsWith("## ")) {
      const headingText = trimmed.replace(/^##\s+/, "");
      return (
        <h3 key={lineIdx} className="mt-3 mb-1.5 font-semibold text-sm text-ink-primary font-mono">
          {headingText}
        </h3>
      );
    }

    // Bullet points (- Point or * Point)
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
              <span key={i}>{part.value}</span>
            ) : (
              <button
                key={i}
                type="button"
                onClick={() => onCitationClick?.(part.value)}
                className="mx-0.5 inline-flex items-center rounded border border-accent-phosphor/40 bg-accent-phosphor/10 px-1.5 py-0.2 font-mono text-[11px] font-medium text-accent-phosphor hover:bg-accent-phosphor/20 transition-colors align-middle"
                title={`View evidence chunk ${part.value}`}
              >
                [{part.value}]
              </button>
            )
          )}
        </div>
      </div>
    );
  };

  return <div className="flex flex-col">{lines.map(renderLine)}</div>;
}
