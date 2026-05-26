"use client";

import { CheckCircle2, Eye, Loader2, Rocket } from "lucide-react";
import Link from "next/link";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import toast from "react-hot-toast";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { InsufficientCreditsModal } from "@/components/InsufficientCreditsModal";
import { ApiError, apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ListingStatusResponse, ListingUploadResponse } from "@/lib/types";

const uploadSteps = [
  "Creating listing on Etsy...",
  "Uploading images...",
  "Uploading video...",
  "Publishing listing..."
];

export default function UploadPage() {
  return (
    <Suspense
      fallback={(
        <Card className="flex min-h-80 items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </Card>
      )}
    >
      <UploadContent />
    </Suspense>
  );
}

function UploadContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const listingId = searchParams.get("listing_id");
  const [accepted, setAccepted] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [manualLoading, setManualLoading] = useState(false);
  const [status, setStatus] = useState<ListingStatusResponse | null>(null);
  const [activeStep, setActiveStep] = useState(0);
  const [insufficientCredits, setInsufficientCredits] = useState<{ required: number; balance: number; action: string } | null>(null);

  const isLive = status?.status === "LIVE";
  const isFailed = status?.status === "FAILED";
  const etsyUrl = status?.etsy_listing_url;

  const pollStatus = useCallback(async () => {
    if (!listingId) return null;
    const response = await apiFetch<ListingStatusResponse>(`/listings/${listingId}/status`);
    setStatus(response);
    return response;
  }, [listingId]);

  useEffect(() => {
    if (!uploading || !listingId) return undefined;

    const progressInterval = window.setInterval(() => {
      setActiveStep((current) => Math.min(current + 1, uploadSteps.length - 1));
    }, 3500);

    const pollInterval = window.setInterval(async () => {
      try {
        const nextStatus = await pollStatus();
        if (nextStatus?.status === "LIVE" || nextStatus?.status === "FAILED") {
          setUploading(false);
        }
      } catch {
        toast.error("Upload in progress...");
      }
    }, 2000);

    return () => {
      window.clearInterval(progressInterval);
      window.clearInterval(pollInterval);
    };
  }, [listingId, pollStatus, uploading]);

  async function uploadNow() {
    if (!listingId) return;
    if (!accepted) {
      toast.error("You must accept the disclaimer to continue.");
      return;
    }

    setUploading(true);
    setActiveStep(0);
    setStatus(null);
    try {
      await apiFetch<ListingUploadResponse>(`/listings/${listingId}/upload`, {
        method: "POST",
        json: { mode: "auto", disclaimer_accepted: true }
      });
      await pollStatus();
    } catch (error) {
      setUploading(false);
      if (error instanceof ApiError && error.code === "INSUFFICIENT_CREDITS") {
        setInsufficientCredits({
          required: Number(error.detail?.required || 0),
          balance: Number(error.detail?.balance || 0),
          action: String(error.detail?.action || "")
        });
        return;
      }
      toast.error(error instanceof Error ? error.message : "Upload failed");
    }
  }

  async function saveManual() {
    if (!listingId) return;
    setManualLoading(true);
    try {
      await apiFetch<ListingUploadResponse>(`/listings/${listingId}/upload`, {
        method: "POST",
        json: { mode: "manual", disclaimer_accepted: false }
      });
      toast.success("Saved to manual review queue");
      router.push("/my-listings");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not save listing");
    } finally {
      setManualLoading(false);
    }
  }

  const completedStep = useMemo(() => {
    if (isLive) return uploadSteps.length;
    if (isFailed) return activeStep;
    return activeStep;
  }, [activeStep, isFailed, isLive]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-950">Upload Listing</h1>
        <p className="mt-1 text-sm text-gray-600">Choose automatic publishing or save the package for manual review.</p>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <Card className="space-y-5">
          <div className="flex items-start gap-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-indigo-50 text-primary">
              <Rocket className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-950">Upload to Etsy Automatically</h2>
              <p className="mt-1 text-sm text-gray-600">We&apos;ll publish your listing directly to your Etsy shop.</p>
            </div>
          </div>

          <div className="max-h-40 overflow-y-auto rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-900">
            By choosing auto-upload, you acknowledge that automated listing creation may violate Etsy&apos;s Terms of Service.
            Your account may be flagged or suspended. ListifyAI is not responsible for any account actions taken by Etsy.
            Use at your own risk.
          </div>

          <label className="flex items-start gap-3 text-sm font-medium text-gray-700">
            <input
              type="checkbox"
              className="mt-1 h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
              checked={accepted}
              onChange={(event) => setAccepted(event.target.checked)}
            />
            <span>I understand and accept the risks</span>
          </label>

          <div className="flex flex-wrap items-center gap-3">
            <Button type="button" disabled={!accepted || uploading} onClick={uploadNow} icon={<Rocket className="h-4 w-4" />}>
              Upload Now
            </Button>
            <span className="text-sm font-medium text-gray-500">(costs 3 credits per listing)</span>
          </div>
        </Card>

        <Card className="space-y-5">
          <div className="flex items-start gap-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700">
              <Eye className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-950">Save to Review Queue</h2>
              <p className="mt-1 text-sm text-gray-600">Download your assets and upload to Etsy yourself. 100% safe.</p>
            </div>
          </div>
          <Button type="button" variant="secondary" loading={manualLoading} onClick={saveManual} icon={<Eye className="h-4 w-4" />}>
            Save to Queue
          </Button>
        </Card>
      </div>

      {uploading || isLive || isFailed ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-950/70 p-4 backdrop-blur-sm">
          <Card className="relative w-full max-w-2xl overflow-hidden">
            {isLive ? <Confetti /> : null}
            <div className="relative space-y-5">
              <div className="text-center">
                <h2 className="text-xl font-bold text-gray-950">
                  {isLive ? "Your listing is live on Etsy! 🎉" : isFailed ? "Upload failed" : "Upload in progress..."}
                </h2>
                {isLive && etsyUrl ? (
                  <a className="mt-3 inline-block text-sm font-semibold text-primary" href={etsyUrl} target="_blank" rel="noreferrer">
                    View on Etsy
                  </a>
                ) : null}
                {isFailed ? (
                  <p className="mt-3 text-sm text-red-600">{status?.error_message || "Upload failed after retries."}</p>
                ) : null}
              </div>

              <div className="space-y-3">
                {uploadSteps.map((step, index) => {
                  const done = completedStep > index || isLive;
                  const active = !isFailed && !isLive && completedStep === index;
                  return (
                    <div key={step} className="flex items-center gap-3 rounded-lg border border-gray-100 bg-gray-50 px-4 py-3">
                      <div className={cn(
                        "flex h-8 w-8 items-center justify-center rounded-full",
                        done ? "bg-emerald-100 text-emerald-700" : isFailed && index === completedStep ? "bg-red-100 text-red-700" : "bg-white text-gray-400"
                      )}>
                        {done ? <CheckCircle2 className="h-4 w-4" /> : active ? <Loader2 className="h-4 w-4 animate-spin" /> : index + 1}
                      </div>
                      <span className="text-sm font-medium text-gray-800">{step}</span>
                    </div>
                  );
                })}
              </div>

              {isFailed ? (
                <div className="flex flex-wrap justify-center gap-3">
                  <Button type="button" onClick={uploadNow} icon={<Rocket className="h-4 w-4" />}>
                    Try Again
                  </Button>
                  <Button type="button" variant="secondary" onClick={saveManual} icon={<Eye className="h-4 w-4" />}>
                    Switch to Manual
                  </Button>
                </div>
              ) : null}

              {isLive ? (
                <div className="flex justify-center">
                  <Link href="/my-listings" className="inline-flex min-h-10 items-center justify-center rounded-md bg-primary px-4 text-sm font-semibold text-white hover:bg-indigo-500">
                    Back to My Listings
                  </Link>
                </div>
              ) : null}
            </div>
          </Card>
        </div>
      ) : null}
      <InsufficientCreditsModal
        isOpen={Boolean(insufficientCredits)}
        onClose={() => setInsufficientCredits(null)}
        required={insufficientCredits?.required || 0}
        balance={insufficientCredits?.balance || 0}
        action={insufficientCredits?.action || ""}
      />
    </div>
  );
}

function Confetti() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {Array.from({ length: 18 }).map((_, index) => (
        <span
          key={index}
          className="absolute h-2 w-2 animate-bounce rounded-sm bg-primary"
          style={{
            left: `${(index * 13) % 100}%`,
            top: `${(index * 19) % 80}%`,
            animationDelay: `${index * 80}ms`
          }}
        />
      ))}
    </div>
  );
}
