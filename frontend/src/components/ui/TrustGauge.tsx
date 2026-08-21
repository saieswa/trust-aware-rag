"use client";

import { TRUST_THRESHOLD_HIGH, TRUST_THRESHOLD_LOW, decisionColorVar } from "@/lib/utils";
import type { Decision } from "@/types/api";

interface TrustGaugeProps {
  score: number;
  decision?: Decision;
  size?: "compact" | "large";
  label?: string;
}

/**
 * The project's signature visual element: trust scores are a calibrated
 * reading from a weighted formula (trust/formula/trust_formula.py), not a
 * marketing metric — so they're drawn as an analog instrument dial, not a
 * colored pill or a progress bar. The needle sweeps across a semicircle
 * from red (0.0) through amber (~0.5) to green (1.0), with tick marks at
 * the REAL configured thresholds (0.5 / 0.75) rather than arbitrary
 * decoration.
 *
 * Two sizes: "compact" for inline use in chat messages and evidence
 * cards, "large" for the Trust Dashboard's headline stat.
 */
export function TrustGauge({ score, decision, size = "compact", label }: TrustGaugeProps) {
  const clamped = Math.min(Math.max(score, 0), 1);
  const dimension = size === "large" ? 200 : 88;
  const strokeWidth = size === "large" ? 14 : 8;
  const radius = dimension / 2 - strokeWidth;
  const cx = dimension / 2;
  const cy = dimension / 2;

  const angleForValue = (v: number) => 180 - v * 180;

  const start = polarToCartesian(cx, cy, radius, 180);
  const end = polarToCartesian(cx, cy, radius, 0);
  const trackPath = `M ${start.x} ${cy} A ${radius} ${radius} 0 0 1 ${end.x} ${cy}`;

  const needleAngle = angleForValue(clamped);
  const needleLength = radius - strokeWidth / 2;
  const needleTip = polarToCartesian(cx, cy, needleLength, needleAngle);

  const color = decision ? decisionColorVar(decision) : scoreColor(clamped);

  const thresholdTick = (value: number) => {
    const angle = angleForValue(value);
    const inner = polarToCartesian(cx, cy, radius - strokeWidth, angle);
    const outer = polarToCartesian(cx, cy, radius + strokeWidth * 0.4, angle);
    return { inner, outer };
  };
  const lowTick = thresholdTick(TRUST_THRESHOLD_LOW);
  const highTick = thresholdTick(TRUST_THRESHOLD_HIGH);

  return (
    <div className="inline-flex flex-col items-center gap-1">
      <svg
        width={dimension}
        height={dimension / 2 + strokeWidth}
        viewBox={`0 0 ${dimension} ${dimension / 2 + strokeWidth}`}
        role="img"
        aria-label={`Trust score ${(clamped * 100).toFixed(0)} percent`}
      >
        <defs>
          <linearGradient id={`gauge-gradient-${size}`} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="var(--signal-red)" />
            <stop offset="50%" stopColor="var(--accent-phosphor)" />
            <stop offset="100%" stopColor="var(--signal-green)" />
          </linearGradient>
        </defs>

        <path d={trackPath} fill="none" stroke="var(--bg-raised)" strokeWidth={strokeWidth} strokeLinecap="round" />
        <path
          d={trackPath}
          fill="none"
          stroke={`url(#gauge-gradient-${size})`}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          opacity={0.35}
        />

        <line x1={lowTick.inner.x} y1={lowTick.inner.y} x2={lowTick.outer.x} y2={lowTick.outer.y} stroke="var(--ink-muted)" strokeWidth={1.5} />
        <line x1={highTick.inner.x} y1={highTick.inner.y} x2={highTick.outer.x} y2={highTick.outer.y} stroke="var(--ink-muted)" strokeWidth={1.5} />

        <line
          x1={cx}
          y1={cy}
          x2={needleTip.x}
          y2={needleTip.y}
          stroke={color}
          strokeWidth={size === "large" ? 3 : 2}
          strokeLinecap="round"
          className="transition-all duration-700 ease-out"
        />
        <circle cx={cx} cy={cy} r={size === "large" ? 5 : 3} fill={color} />
      </svg>
      <div className="flex flex-col items-center -mt-1">
        <span className="font-mono font-semibold tabular-nums" style={{ color, fontSize: size === "large" ? "2rem" : "1rem" }}>
          {clamped.toFixed(2)}
        </span>
        {label && <span className="text-xs text-ink-muted">{label}</span>}
      </div>
    </div>
  );
}

function polarToCartesian(cx: number, cy: number, radius: number, angleDeg: number) {
  const angleRad = (angleDeg * Math.PI) / 180;
  return {
    x: cx + radius * Math.cos(angleRad),
    y: cy - radius * Math.sin(angleRad),
  };
}

function scoreColor(value: number): string {
  if (value >= TRUST_THRESHOLD_HIGH) return "var(--signal-green)";
  if (value >= TRUST_THRESHOLD_LOW) return "var(--accent-phosphor)";
  return "var(--signal-red)";
}
