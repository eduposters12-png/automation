"use client";

import {
  ArrowRight,
  BarChart3,
  CheckCircle2,
  DollarSign,
  Loader2,
  RefreshCw,
  Sparkles,
  Tags
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ProductIdea, ProductPotential, ShopAnalysis, ShopAnalysisResponse } from "@/lib/types";

const progressSteps = [
  "Connecting to your Etsy shop...",
  "Fetching your listings and sales data...",
  "Finding trending opportunities...",
  "Claude is analyzing your shop..."
];

function potentialTone(potential: ProductPotential): "green" | "amber" | "gray" {
  if (potential === "High") return "green";
  if (potential === "Medium") return "amber";
  return "gray";
}

function formatPrice(value: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value);
}

function formatRelativeTime(value: string | null) {
  if (!value) return "Not analyzed yet";

  const diffMs = Date.now() - new Date(value).getTime();
  const minutes = Math.max(1, Math.floor(diffMs / 60000));
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? "" : "s"} ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;

  const days = Math.floor(hours / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

function listingHref(idea: ProductIdea, index: number) {
  const params = new URLSearchParams({ product_idea: idea.title, product_idea_index: String(index) });
  if (Number.isFinite(idea.suggestedPrice)) {
    params.set("target_price", String(idea.suggestedPrice));
  }
  return `/new-listing?${params.toString()}`;
}

function ProgressSteps({ activeStep }: { activeStep: number }) {
  return (
    <Card className="space-y-4">
      {progressSteps.map((step, index) => {
        const isActive = index === activeStep;
        const isDone = index < activeStep;
        return (
          <div key={step} className="flex items-center gap-3">
            <div
              className={cn(
                "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-sm",
                isDone && "border-emerald-200 bg-emerald-50 text-emerald-700",
                isActive && "border-indigo-200 bg-indigo-50 text-primary",
                !isDone && !isActive && "border-gray-200 bg-gray-50 text-gray-400"
              )}
            >
              {isDone ? (
                <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
              ) : isActive ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                index + 1
              )}
            </div>
            <span className={cn("text-sm font-medium", isActive ? "text-gray-950" : "text-gray-500")}>{step}</span>
          </div>
        );
      })}
    </Card>
  );
}

function AnalysisView({
  analysis,
  lastAnalyzedAt,
  analyzing,
  onAnalyze
}: {
  analysis: ShopAnalysis;
  lastAnalyzedAt: string | null;
  analyzing: boolean;
  onAnalyze: () => Promise<void>;
}) {
  return (
    <div className="space-y-6">
      <Card>
        <div className="min-w-0">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-primary">
            <BarChart3 className="h-4 w-4" aria-hidden="true" />
            Shop Overview
          </div>
          <h2 className="text-xl font-bold text-gray-950">{analysis.niche}</h2>
          <p className="mt-2 text-sm text-gray-600">{analysis.style}</p>
          <div className="mt-4 flex flex-wrap gap-2">
            {analysis.strengths.map((strength) => (
              <Badge key={strength} tone="indigo" className="max-w-full break-words">
                {strength}
              </Badge>
            ))}
          </div>
        </div>
      </Card>

      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-primary" aria-hidden="true" />
          <h2 className="text-lg font-bold text-gray-950">Opportunities</h2>
        </div>
        <div className="grid gap-4 lg:grid-cols-3">
          {analysis.opportunities.map((opportunity) => (
            <Card key={opportunity.title} className="min-h-40">
              <h3 className="text-base font-semibold text-gray-950">{opportunity.title}</h3>
              <p className="mt-3 text-sm leading-6 text-gray-600">{opportunity.description}</p>
            </Card>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <Tags className="h-5 w-5 text-primary" aria-hidden="true" />
          <h2 className="text-lg font-bold text-gray-950">Product Ideas</h2>
        </div>
        <div className="grid gap-4 xl:grid-cols-2">
          {analysis.productIdeas.map((idea, index) => (
            <Card key={idea.title} className="flex min-h-[320px] flex-col">
              <div className="flex items-start justify-between gap-3">
                <h3 className="min-w-0 text-base font-semibold text-gray-950">{idea.title}</h3>
                <Badge tone={potentialTone(idea.potential)}>{idea.potential}</Badge>
              </div>
              <p className="mt-3 text-sm leading-6 text-gray-600">{idea.descriptionIdea}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                {idea.targetKeywords.map((keyword) => (
                  <Badge key={keyword} tone="gray" className="break-words">
                    {keyword}
                  </Badge>
                ))}
              </div>
              <div className="mt-4 flex items-center gap-2 text-sm font-semibold text-gray-950">
                <DollarSign className="h-4 w-4 text-emerald-600" aria-hidden="true" />
                {formatPrice(idea.suggestedPrice)}
              </div>
              <p className="mt-3 text-sm leading-6 text-gray-500">{idea.rationale}</p>
              <div className="mt-auto pt-5">
                <Link
                  href={listingHref(idea, index)}
                  className="inline-flex min-h-10 items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-semibold text-white transition hover:bg-indigo-500"
                >
                  Generate Listing
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Link>
              </div>
            </Card>
          ))}
        </div>
      </section>

      <Card className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="text-sm text-gray-500">Last analyzed: {formatRelativeTime(lastAnalyzedAt)}</div>
        <Button
          type="button"
          variant="secondary"
          onClick={onAnalyze}
          loading={analyzing}
          icon={<RefreshCw className="h-4 w-4" aria-hidden="true" />}
        >
          Re-analyze
        </Button>
      </Card>
    </div>
  );
}

export default function ShopAnalysisPage() {
  const [analysis, setAnalysis] = useState<ShopAnalysis | null>(null);
  const [lastAnalyzedAt, setLastAnalyzedAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    let active = true;

    async function loadAnalysis() {
      try {
        const response = await apiFetch<ShopAnalysisResponse>("/shop/analysis");
        if (!active) return;
        if (response.analyzed && response.analysis) {
          setAnalysis(response.analysis);
          setLastAnalyzedAt(response.last_analyzed_at || null);
        }
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "Could not load analysis");
      } finally {
        if (active) setLoading(false);
      }
    }

    void loadAnalysis();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!analyzing) return undefined;
    const interval = window.setInterval(() => {
      setActiveStep((step) => Math.min(step + 1, progressSteps.length - 1));
    }, 1800);
    return () => window.clearInterval(interval);
  }, [analyzing]);

  async function runAnalysis() {
    setAnalyzing(true);
    setActiveStep(0);
    try {
      const nextAnalysis = await apiFetch<ShopAnalysis>("/shop/analyze", { method: "POST" });
      setAnalysis(nextAnalysis);
      setLastAnalyzedAt(new Date().toISOString());
      toast.success("Shop analysis complete");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Shop analysis failed");
    } finally {
      setAnalyzing(false);
      setActiveStep(0);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-950">Shop Analysis</h1>
        <p className="mt-1 text-sm text-gray-600">Marketplace intelligence for your connected Etsy shop.</p>
      </div>

      {loading ? (
        <Card className="flex min-h-48 items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-primary" aria-hidden="true" />
        </Card>
      ) : analyzing ? (
        <ProgressSteps activeStep={activeStep} />
      ) : analysis ? (
        <AnalysisView
          analysis={analysis}
          lastAnalyzedAt={lastAnalyzedAt}
          analyzing={analyzing}
          onAnalyze={runAnalysis}
        />
      ) : (
        <Card className="flex min-h-64 flex-col items-center justify-center text-center">
          <div className="min-w-0">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-md bg-indigo-50 text-primary">
              <Sparkles className="h-6 w-6" aria-hidden="true" />
            </div>
            <h2 className="mt-4 text-lg font-semibold text-gray-950">No analysis yet</h2>
            <Button type="button" className="mt-5" onClick={runAnalysis} loading={analyzing}>
              Analyze My Shop
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
