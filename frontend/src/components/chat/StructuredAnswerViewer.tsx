"use client";

import React from "react";
import {
  FileText,
  Target,
  ListOrdered,
  Key,
  TrendingUp,
  Brain,
  HelpCircle,
  CheckCircle2,
  Quote,
  Layers,
} from "lucide-react";
import type { StructuredAnswer } from "@/types/api";

interface StructuredAnswerViewerProps {
  structuredAnswer?: StructuredAnswer | null;
  rawText?: string;
  onCitationClick?: (chunkId: string) => void;
}

// Clean internal chunk IDs like [doc_xxx_chunk0] or [chunk_xxx]
function stripInternalIds(text: string): string {
  if (!text) return "";
  return text.replace(/\[(?:doc_[a-zA-Z0-9_]+|chunk_[a-zA-Z0-9_]+|[a-zA-Z0-9_]+_chunk\d+)\]/g, "").trim();
}

// Clean markdown formatting symbols like **, *, `
function cleanMarkdownSymbols(text: string): string {
  if (!text) return "";
  return text
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/\*(.*?)\*/g, "$1")
    .replace(/__(.*?)__/g, "$1")
    .replace(/`(.*?)`/g, "$1")
    .trim();
}

export function StructuredAnswerViewer({ structuredAnswer, rawText, onCitationClick }: StructuredAnswerViewerProps) {
  // If backend provided rich structured_answer, use it directly
  if (structuredAnswer && (structuredAnswer.document_overview || structuredAnswer.direct_answer || (structuredAnswer.steps && structuredAnswer.steps.length > 0))) {
    return <RenderStructuredData data={structuredAnswer} onCitationClick={onCitationClick} />;
  }

  // Otherwise, parse rawText markdown into structured sections
  const parsed = parseRawMarkdown(rawText || "");
  return <RenderStructuredData data={parsed} onCitationClick={onCitationClick} />;
}

function parseRawMarkdown(text: string): StructuredAnswer {
  const lines = text.split("\n");
  let currentSection = "direct_answer";
  const overviewLines: string[] = [];
  const ideaLines: string[] = [];
  const steps: string[] = [];
  const keyPoints: string[] = [];
  const mainFindings: string[] = [];
  const simpleExpLines: string[] = [];
  const directAnswerLines: string[] = [];
  let evidenceSummary = "";
  let sourceSummary = "";

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;

    const lower = trimmed.toLowerCase();
    if (lower.startsWith("### document overview") || lower.startsWith("## document overview") || lower.startsWith("### 📄 document overview")) {
      currentSection = "overview";
      continue;
    }
    if (lower.startsWith("### main idea") || lower.startsWith("## main idea") || lower.startsWith("### 🎯 main purpose") || lower.startsWith("### main purpose")) {
      currentSection = "idea";
      continue;
    }
    if (lower.startsWith("### step-by-step") || lower.startsWith("## step-by-step") || lower.startsWith("### steps")) {
      currentSection = "steps";
      continue;
    }
    if (lower.startsWith("### key points") || lower.startsWith("## key points") || lower.startsWith("### 🔑 key concepts") || lower.startsWith("### key concepts")) {
      currentSection = "key_points";
      continue;
    }
    if (lower.startsWith("### main findings") || lower.startsWith("## main findings") || lower.startsWith("### 📌 main findings")) {
      currentSection = "findings";
      continue;
    }
    if (lower.startsWith("### simple explanation") || lower.startsWith("## simple explanation") || lower.startsWith("### 🧠 simple explanation")) {
      currentSection = "simple";
      continue;
    }
    if (lower.startsWith("### answer") || lower.startsWith("## answer")) {
      currentSection = "answer";
      continue;
    }
    if (lower.startsWith("### evidence") || lower.startsWith("## evidence") || lower.startsWith("### 📚 evidence used")) {
      currentSection = "evidence";
      continue;
    }
    if (lower.startsWith("### source") || lower.startsWith("## source")) {
      currentSection = "source";
      continue;
    }

    const cleanLine = cleanMarkdownSymbols(stripInternalIds(trimmed));
    if (!cleanLine) continue;

    if (currentSection === "overview") {
      overviewLines.push(cleanLine);
    } else if (currentSection === "idea") {
      ideaLines.push(cleanLine);
    } else if (currentSection === "steps") {
      const stepText = cleanLine.replace(/^\d+[\.\)]\s*/, "").replace(/^[-*•]\s*/, "");
      steps.push(stepText);
    } else if (currentSection === "key_points") {
      const pointText = cleanLine.replace(/^[-*•]\s*/, "");
      keyPoints.push(pointText);
    } else if (currentSection === "findings") {
      const findText = cleanLine.replace(/^[-*•]\s*/, "");
      mainFindings.push(findText);
    } else if (currentSection === "simple") {
      simpleExpLines.push(cleanLine);
    } else if (currentSection === "answer") {
      directAnswerLines.push(cleanLine);
    } else if (currentSection === "evidence") {
      evidenceSummary = evidenceSummary ? `${evidenceSummary} ${cleanLine}` : cleanLine;
    } else if (currentSection === "source") {
      sourceSummary = sourceSummary ? `${sourceSummary} ${cleanLine}` : cleanLine;
    } else {
      directAnswerLines.push(cleanLine);
    }
  }

  const isDocLevel = overviewLines.length > 0 || ideaLines.length > 0 || steps.length > 0;

  return {
    answer_type: isDocLevel ? "document_explanation" : "specific_answer",
    document_overview: overviewLines.join(" "),
    main_idea: ideaLines.join(" "),
    steps,
    key_points: keyPoints,
    main_findings: mainFindings,
    simple_explanation: simpleExpLines.join(" "),
    direct_answer: directAnswerLines.join(" "),
  };
}

function RenderStructuredData({
  data,
  onCitationClick,
}: {
  data: StructuredAnswer;
  onCitationClick?: (chunkId: string) => void;
}) {
  // If specific answer layout
  if (data.answer_type === "specific_answer" || (!data.document_overview && !data.main_idea && (!data.steps || data.steps.length === 0))) {
    return (
      <div className="flex flex-col gap-3.5">
        {data.direct_answer && (
          <div className="rounded-lg bg-panel border border-hairline p-4 shadow-sm">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 className="h-4 w-4 text-accent-phosphor" />
              <span className="text-xs font-semibold uppercase tracking-wider text-ink-primary font-mono">
                Direct Answer
              </span>
            </div>
            <p className="text-sm leading-relaxed text-ink-primary font-normal">
              {stripInternalIds(data.direct_answer)}
            </p>
          </div>
        )}
      </div>
    );
  }

  // Document-Level Structured Layout
  return (
    <div className="flex flex-col gap-4">
      {/* 1. Document Overview */}
      {data.document_overview && (
        <div className="rounded-lg bg-panel border border-hairline p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <FileText className="h-4 w-4 text-accent-phosphor" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-primary font-mono">
              1. Document Overview
            </h3>
          </div>
          <p className="text-sm leading-relaxed text-ink-primary">
            {stripInternalIds(data.document_overview)}
          </p>
        </div>
      )}

      {/* 2. Main Idea */}
      {data.main_idea && (
        <div className="rounded-lg bg-panel border border-hairline p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <Target className="h-4 w-4 text-emerald-400" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-primary font-mono">
              2. Main Idea
            </h3>
          </div>
          <p className="text-sm leading-relaxed text-ink-primary">
            {stripInternalIds(data.main_idea)}
          </p>
        </div>
      )}

      {/* 3. Step-by-Step Explanation */}
      {data.steps && data.steps.length > 0 && (
        <div className="rounded-lg bg-panel border border-hairline p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-3">
            <ListOrdered className="h-4 w-4 text-amber-400" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-primary font-mono">
              3. Step-by-Step Explanation
            </h3>
          </div>
          <div className="flex flex-col gap-2.5">
            {data.steps.map((step, idx) => (
              <div key={idx} className="flex items-start gap-3 rounded bg-raised/60 border border-hairline/60 p-2.5">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent-phosphor/20 text-accent-phosphor font-mono text-xs font-bold mt-0.5">
                  {idx + 1}
                </span>
                <p className="text-sm leading-relaxed text-ink-primary flex-1">
                  {stripInternalIds(step)}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 4. Key Points */}
      {data.key_points && data.key_points.length > 0 && (
        <div className="rounded-lg bg-panel border border-hairline p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-3">
            <Key className="h-4 w-4 text-cyan-400" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-primary font-mono">
              4. Key Points
            </h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {data.key_points.map((pt, idx) => (
              <div key={idx} className="flex items-start gap-2.5 rounded bg-raised/50 border border-hairline/50 p-2.5">
                <span className="text-accent-phosphor font-bold text-base leading-none mt-0.5">•</span>
                <p className="text-xs leading-relaxed text-ink-primary">
                  {stripInternalIds(pt)}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 5. Main Findings / Topics */}
      {data.main_findings && data.main_findings.length > 0 && (
        <div className="rounded-lg bg-panel border border-hairline p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="h-4 w-4 text-purple-400" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-primary font-mono">
              5. Main Findings &amp; Topics
            </h3>
          </div>
          <div className="flex flex-col gap-2">
            {data.main_findings.map((f, idx) => (
              <div key={idx} className="flex items-start gap-2.5 rounded bg-raised/50 border border-hairline/50 p-2.5">
                <span className="text-purple-400 font-bold text-base leading-none mt-0.5">•</span>
                <p className="text-xs leading-relaxed text-ink-primary">
                  {stripInternalIds(f)}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 6. Simple Explanation */}
      {data.simple_explanation && (
        <div className="rounded-lg bg-panel border border-hairline p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <Brain className="h-4 w-4 text-rose-400" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-primary font-mono">
              6. Simple Explanation
            </h3>
          </div>
          <p className="text-sm leading-relaxed text-ink-primary">
            {stripInternalIds(data.simple_explanation)}
          </p>
        </div>
      )}
    </div>
  );
}
