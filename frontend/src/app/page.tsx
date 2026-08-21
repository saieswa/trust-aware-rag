import Link from "next/link";
import { ArrowRight, ShieldCheck, GitCompareArrows, ShieldQuestion } from "lucide-react";
import { PipelineHero } from "@/components/layout/PipelineHero";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";

const PRINCIPLES = [
  {
    icon: ShieldCheck,
    title: "Every claim cites its evidence",
    body: "The Synthesizer only writes from evidence the Critic Agent already marked as supporting — and every sentence names the exact chunk it came from.",
  },
  {
    icon: GitCompareArrows,
    title: "Contradictions surface, not blend",
    body: "When two sources disagree, the system doesn't average them into a vague answer — it flags the conflict and picks the more reliable side, visibly.",
  },
  {
    icon: ShieldQuestion,
    title: "Below threshold, it says so",
    body: "The trust score is a calibrated reading, not a vibe. Fall below it, and the system abstains instead of guessing.",
  },
];

export default function HomePage() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-12 md:py-20">
      <div className="flex flex-col items-center text-center gap-4">
        <span className="font-mono text-xs uppercase tracking-[0.2em] text-accent-phosphor">
          Trust-Aware Multi-Agent RAG
        </span>
        <h1 className="font-mono text-3xl md:text-5xl font-semibold text-ink-primary max-w-2xl leading-tight">
          An answer is only as good as the evidence behind it.
        </h1>
        <p className="max-w-xl text-sm md:text-base text-ink-muted">
          Four agents — Retriever, Critic, Synthesizer, Verifier — read the same evidence you can, and a calibrated
          trust score decides whether to answer, dig deeper, or admit it doesn&rsquo;t know.
        </p>
        <div className="flex gap-3 mt-2">
          <Link href="/chat">
            <Button>
              Ask a question <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
          <Link href="/dashboard">
            <Button variant="secondary">View trust dashboard</Button>
          </Link>
        </div>
      </div>

      <PipelineHero />

      <div className="grid gap-4 sm:grid-cols-3 mt-8">
        {PRINCIPLES.map((p) => (
          <Card key={p.title}>
            <CardBody className="flex flex-col gap-2">
              <p.icon className="h-5 w-5 text-accent-phosphor" />
              <h3 className="text-sm font-medium text-ink-primary">{p.title}</h3>
              <p className="text-xs text-ink-muted leading-relaxed">{p.body}</p>
            </CardBody>
          </Card>
        ))}
      </div>
    </div>
  );
}
