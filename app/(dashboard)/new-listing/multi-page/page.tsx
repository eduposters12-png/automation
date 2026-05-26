"use client";

import { ArrowRight, Download, FileText, Loader2, RefreshCw, Sparkles } from "lucide-react";
import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

type Phase = "setup" | "generating" | "complete" | "failed";

type CreateResponse = {
  listing_id: string;
  status: string;
};

type PageImage = {
  page_number: number;
  image_url: string;
  approved: boolean;
};

type MultiPageStatus = {
  listing_id: string;
  status: string;
  total_pages_planned: number | null;
  pages_completed: number;
  progress_percent: number;
  page_images: PageImage[];
  pdf_url: string | null;
  error_message: string | null;
};

type PagePlan = {
  page_plan: Record<string, unknown> | null;
  total_pages: number | null;
  reasoning: string | null;
  pages: { page_number: number; page_title: string }[] | null;
};

export default function MultiPageListingPage() {
  const [productIdea, setProductIdea] = useState("");
  const [styleNotes, setStyleNotes] = useState("");
  const [listingId, setListingId] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>("setup");
  const [statusData, setStatusData] = useState<MultiPageStatus | null>(null);
  const [pagePlan, setPagePlan] = useState<PagePlan | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [starting, setStarting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const totalPages = statusData?.total_pages_planned || pagePlan?.total_pages || 0;
  const completedPages = statusData?.pages_completed || 0;
  const progressPercent = useMemo(() => {
    if (statusData?.progress_percent !== undefined) return statusData.progress_percent;
    return totalPages ? Math.round((completedPages / totalPages) * 100) : 0;
  }, [completedPages, statusData?.progress_percent, totalPages]);

  const loadStatus = useCallback(async (id: string) => {
    const data = await apiFetch<MultiPageStatus>(`/listings/${id}/multi-page-status`);
    setStatusData(data);
    if (data.status === "COPY_READY") {
      setPhase("complete");
    }
    if (data.status === "FAILED") {
      setPhase("failed");
      setErrorMessage(data.error_message || "Generation failed. Please try again.");
    }
  }, []);

  const loadPlan = useCallback(async (id: string) => {
    const data = await apiFetch<PagePlan>(`/listings/${id}/page-plan`);
    setPagePlan(data);
  }, []);

  const startGeneration = useCallback(async (id: string) => {
    setStarting(true);
    setErrorMessage("");
    try {
      await apiFetch<{ success: boolean; total_pages: number; pdf_url: string | null }>(`/listings/${id}/start-multi-page`, {
        method: "POST"
      });
      await loadStatus(id);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not start generation.";
      setErrorMessage(message);
      setPhase("failed");
      toast.error(message);
    } finally {
      setStarting(false);
    }
  }, [loadStatus]);

  async function createAndStart(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!productIdea.trim()) return;

    setSubmitting(true);
    setErrorMessage("");
    try {
      const created = await apiFetch<CreateResponse>("/listings/create-multi-page", {
        method: "POST",
        json: {
          product_idea: productIdea.trim(),
          style_notes: styleNotes.trim()
        }
      });
      setListingId(created.listing_id);
      setPhase("generating");
      toast.success("Multi-page product queued");
      void startGeneration(created.listing_id);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not create multi-page listing.";
      setErrorMessage(message);
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  }

  async function tryAgain() {
    if (!listingId) return;
    setPhase("generating");
    setStatusData(null);
    setPagePlan(null);
    void startGeneration(listingId);
  }

  useEffect(() => {
    if (!listingId || phase !== "generating") return undefined;
    void loadStatus(listingId).catch(() => undefined);
    const interval = window.setInterval(() => {
      void loadStatus(listingId).catch(() => undefined);
    }, 3000);
    return () => window.clearInterval(interval);
  }, [listingId, loadStatus, phase]);

  useEffect(() => {
    if (!listingId || phase !== "generating" || pagePlan?.page_plan) return undefined;
    void loadPlan(listingId).catch(() => undefined);
    const interval = window.setInterval(() => {
      void loadPlan(listingId).catch(() => undefined);
    }, 3000);
    return () => window.clearInterval(interval);
  }, [listingId, loadPlan, pagePlan?.page_plan, phase]);

  if (phase === "setup") {
    return (
      <div className="max-w-4xl space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-950">Create Multi-Page Digital Product</h1>
          <p className="mt-1 text-sm text-gray-600">Let Claude plan the page count, prompts, and printable PDF structure.</p>
        </div>

        <Card>
          <form className="space-y-5" onSubmit={createAndStart}>
            <label className="block" htmlFor="product-idea">
              <span className="mb-2 block text-sm font-medium text-gray-800">What is your product?</span>
              <textarea
                id="product-idea"
                className="min-h-36 w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm text-gray-950 outline-none transition placeholder:text-gray-400 focus:border-primary focus:ring-2 focus:ring-indigo-100"
                value={productIdea}
                onChange={(event) => setProductIdea(event.target.value)}
                placeholder="e.g. USA History Timeline Posters 1776-2026"
                minLength={5}
                maxLength={500}
                required
              />
            </label>

            <label className="block" htmlFor="style-notes">
              <span className="mb-2 block text-sm font-medium text-gray-800">Style notes (optional)</span>
              <textarea
                id="style-notes"
                className="min-h-24 w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm text-gray-950 outline-none transition placeholder:text-gray-400 focus:border-primary focus:ring-2 focus:ring-indigo-100"
                value={styleNotes}
                onChange={(event) => setStyleNotes(event.target.value)}
                placeholder="e.g. vintage gold borders, educational clean layout"
              />
            </label>

            {errorMessage ? (
              <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
                {errorMessage}
              </div>
            ) : null}

            <Button type="submit" loading={submitting} icon={<Sparkles className="h-4 w-4" aria-hidden="true" />}>
              Plan with Claude -&gt;
            </Button>
          </form>
        </Card>
      </div>
    );
  }

  if (phase === "failed") {
    return (
      <Card className="max-w-2xl space-y-4">
        <h1 className="text-xl font-bold text-gray-950">Generation failed</h1>
        <p className="text-sm leading-6 text-gray-600">{errorMessage || "Something went wrong while generating this product."}</p>
        <Button type="button" onClick={tryAgain} loading={starting} icon={<RefreshCw className="h-4 w-4" aria-hidden="true" />}>
          Try Again
        </Button>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-950">
            {phase === "complete" ? `Your ${totalPages || completedPages}-page product is ready!` : "Claude is building your product..."}
          </h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-gray-600">
            {pagePlan?.reasoning || "Claude is planning the product structure and generating each printable page."}
          </p>
        </div>

        {phase === "complete" && statusData?.pdf_url ? (
          <a
            href={statusData.pdf_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-semibold text-white transition hover:bg-indigo-500"
          >
            <Download className="h-4 w-4" aria-hidden="true" />
            Download PDF
          </a>
        ) : null}
      </div>

      <Card className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3 text-sm font-semibold text-gray-700">
            {phase === "generating" ? <Loader2 className="h-4 w-4 animate-spin text-primary" /> : <FileText className="h-4 w-4 text-primary" />}
            Page {completedPages} of {totalPages || "..."} generated
          </div>
          <span className="text-sm font-bold text-gray-950">{progressPercent}%</span>
        </div>
        <div className="h-3 overflow-hidden rounded-full bg-gray-100">
          <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${progressPercent}%` }} />
        </div>
      </Card>

      <div className={cn("grid gap-4", statusData?.page_images?.length ? "sm:grid-cols-2 xl:grid-cols-4" : "")}>
        {(statusData?.page_images || []).map((page) => (
          <Card key={`${page.page_number}-${page.image_url}`} className="p-3">
            <div className="overflow-hidden rounded-md border border-gray-100 bg-gray-50">
              <img src={page.image_url} alt={`Generated page ${page.page_number}`} className="aspect-[2/3] w-full object-cover" />
            </div>
            <div className="mt-3 text-sm font-semibold text-gray-700">Page {page.page_number}</div>
          </Card>
        ))}
        {!statusData?.page_images?.length ? (
          <Card className="flex min-h-48 items-center justify-center text-sm font-medium text-gray-500">
            Page thumbnails will appear here as they finish.
          </Card>
        ) : null}
      </div>

      {phase === "complete" && listingId ? (
        <div className="flex justify-end">
          <Link
            href={`/new-listing/package?listing_id=${listingId}`}
            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-semibold text-white transition hover:bg-indigo-500"
          >
            Continue to listing details
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </div>
      ) : null}
    </div>
  );
}
