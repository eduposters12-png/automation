"use client";

import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Download,
  DollarSign,
  FileText,
  Film,
  Loader2,
  Plus,
  RefreshCw,
  Sparkles,
  XCircle
} from "lucide-react";
import Link from "next/link";
import { KeyboardEvent, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import toast from "react-hot-toast";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Modal } from "@/components/ui/Modal";
import { InsufficientCreditsModal } from "@/components/InsufficientCreditsModal";
import { ApiError, apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";
import type {
  AuthResponse,
  GenerateCopyResponse,
  GenerateVideoResponse,
  ListingPackage,
  Plan,
  SuccessResponse
} from "@/lib/types";

type CopyField = "title" | "description" | "tags" | "price";
const VIDEO_TIMEOUT_MS = 120_000;

function canUseVideo(plan: Plan | null) {
  return plan === "PRO" || plan === "AGENCY";
}

function countWords(value: string) {
  const trimmed = value.trim();
  return trimmed ? trimmed.split(/\s+/).length : 0;
}

export default function ListingPackagePage() {
  return (
    <Suspense
      fallback={(
        <Card className="flex min-h-80 items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-primary" aria-hidden="true" />
        </Card>
      )}
    >
      <ListingPackageContent />
    </Suspense>
  );
}

function ListingPackageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const listingId = searchParams.get("listing_id");

  const [plan, setPlan] = useState<Plan | null>(null);
  const [listingPackage, setListingPackage] = useState<ListingPackage | null>(null);
  const [loadingPackage, setLoadingPackage] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [imageIndex, setImageIndex] = useState(0);
  const [videoLoading, setVideoLoading] = useState(false);
  const [videoProgress, setVideoProgress] = useState(0);
  const [copyLoading, setCopyLoading] = useState(false);
  const [savingField, setSavingField] = useState<CopyField | null>(null);
  const [saveErrors, setSaveErrors] = useState<Record<string, string>>({});
  const [upgradeModalOpen, setUpgradeModalOpen] = useState(false);
  const [insufficientCredits, setInsufficientCredits] = useState<{ required: number; balance: number; action: string } | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState("");
  const [price, setPrice] = useState("");
  const [isBundle, setIsBundle] = useState(false);
  const videoDoneRef = useRef(false);

  const images = listingPackage?.image_urls || [];
  const currentImage = images[imageIndex] || images[0] || null;
  const imagesReady = images.length > 0;
  const copyReady = Boolean(title.trim() && description.trim());
  const videoReady = Boolean(listingPackage?.video_url);
  const uploadReady = imagesReady && copyReady;
  const titleTooLong = title.length > 140;
  const wordCount = useMemo(() => countWords(description), [description]);

  const applyPackage = useCallback((data: ListingPackage) => {
    setListingPackage(data);
    setTitle(data.title || "");
    setDescription(data.description || "");
    setTags(data.tags || []);
    setPrice(data.price === null ? "" : String(data.price));
    setIsBundle(data.is_bundle);
    setImageIndex((current) => Math.min(current, Math.max(data.image_urls.length - 1, 0)));
  }, []);

  const loadPackage = useCallback(async (showLoading = true) => {
    if (!listingId) {
      setLoadError("Could not load listing. Please refresh.");
      setLoadingPackage(false);
      return;
    }
    if (showLoading) {
      setLoadingPackage(true);
    }
    setLoadError("");
    try {
      const data = await apiFetch<ListingPackage>(`/listings/${listingId}/package`);
      applyPackage(data);
    } catch {
      setLoadError("Could not load listing. Please refresh.");
    } finally {
      setLoadingPackage(false);
    }
  }, [applyPackage, listingId]);

  useEffect(() => {
    async function loadUserPlan() {
      try {
        const auth = await apiFetch<AuthResponse>("/auth/me");
        setPlan(auth.user.plan);
      } catch {
        setPlan(null);
      }
    }

    void loadUserPlan();
    void loadPackage();
  }, [loadPackage]);

  useEffect(() => {
    if (!videoLoading) return undefined;
    const startedAt = Date.now();
    setVideoProgress(12);
    const interval = window.setInterval(() => {
      if (Date.now() - startedAt >= VIDEO_TIMEOUT_MS) {
        window.clearInterval(interval);
        videoDoneRef.current = true;
        setVideoLoading(false);
        toast.error("Video generation is taking longer than expected. Please try again.");
        return;
      }
      setVideoProgress((current) => Math.min(current + 8, 92));
      if (listingId) {
        void apiFetch<ListingPackage>(`/listings/${listingId}/package`)
          .then((data) => {
            if (data.video_url && !videoDoneRef.current) {
              videoDoneRef.current = true;
              applyPackage(data);
              setVideoProgress(100);
              setVideoLoading(false);
              toast.success("Video generated");
              window.clearInterval(interval);
            }
          })
          .catch(() => undefined);
      }
    }, 3000);
    return () => window.clearInterval(interval);
  }, [applyPackage, listingId, videoLoading]);

  function previousImage() {
    setImageIndex((current) => (images.length ? (current - 1 + images.length) % images.length : 0));
  }

  function nextImage() {
    setImageIndex((current) => (images.length ? (current + 1) % images.length : 0));
  }

  function showInsufficientCredits(error: ApiError) {
    setInsufficientCredits({
      required: Number(error.detail?.required || 0),
      balance: Number(error.detail?.balance || 0),
      action: String(error.detail?.action || "")
    });
  }

  async function generateVideo() {
    if (!listingId) return;
    if (plan && !canUseVideo(plan)) {
      setUpgradeModalOpen(true);
      return;
    }

    setVideoLoading(true);
    videoDoneRef.current = false;
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), VIDEO_TIMEOUT_MS);
    try {
      const response = await apiFetch<GenerateVideoResponse>(`/listings/${listingId}/generate-video`, {
        method: "POST",
        signal: controller.signal
      });
      if (!videoDoneRef.current) {
        videoDoneRef.current = true;
        setListingPackage((current) => current ? { ...current, video_url: response.video_url } : current);
        setVideoProgress(100);
        toast.success("Video generated");
        await loadPackage(false);
      }
    } catch (error) {
      if (videoDoneRef.current) {
        return;
      }
      if (error instanceof Error && error.name === "AbortError") {
        toast.error("Video generation is taking longer than expected. Please try again.");
        return;
      }
      if (error instanceof ApiError && error.code === "INSUFFICIENT_CREDITS") {
        showInsufficientCredits(error);
        return;
      }
      const message = error instanceof Error ? error.message : "Video generation failed. Please try again.";
      if (message.includes("Pro plan")) {
        setUpgradeModalOpen(true);
      } else if (message.includes("No approved images")) {
        toast.error("Please approve at least one image before generating video.");
      } else {
        toast.error("Video generation failed. Please try again.");
      }
    } finally {
      window.clearTimeout(timeout);
      setVideoLoading(false);
    }
  }

  async function generateCopy() {
    if (!listingId) return;
    setCopyLoading(true);
    try {
      const response = await apiFetch<GenerateCopyResponse>(`/listings/${listingId}/generate-copy`, {
        method: "POST"
      });
      setTitle(response.title);
      setDescription(response.description);
      setTags(response.tags);
      setPrice(String(response.suggestedPrice));
      setListingPackage((current) => current ? {
        ...current,
        title: response.title,
        description: response.description,
        tags: response.tags,
        price: response.suggestedPrice,
        status: "COPY_READY"
      } : current);
      toast.success("Copy generated");
    } catch (error) {
      if (error instanceof ApiError && error.code === "INSUFFICIENT_CREDITS") {
        showInsufficientCredits(error);
        return;
      }
      toast.error("Copy generation failed. Check your Claude API key in settings.");
    } finally {
      setCopyLoading(false);
    }
  }

  async function saveCopyField(field: CopyField, value: unknown) {
    if (!listingId) return;
    setSavingField(field);
    setSaveErrors((current) => {
      const next = { ...current };
      delete next[field];
      return next;
    });

    try {
      await apiFetch<SuccessResponse>(`/listings/${listingId}/copy`, {
        method: "PATCH",
        json: { [field]: value }
      });
      setListingPackage((current) => {
        if (!current) return current;
        const next = { ...current };
        if (field === "title") {
          next.title = typeof value === "string" ? value : null;
        }
        if (field === "description") {
          next.description = typeof value === "string" ? value : null;
        }
        if (field === "tags") {
          next.tags = Array.isArray(value) ? value.map(String) : [];
        }
        if (field === "price") {
          next.price = typeof value === "number" ? value : null;
        }
        next.status = current.status === "IMAGE_APPROVED" ? "COPY_READY" : current.status;
        return next;
      });
    } catch {
      setSaveErrors((current) => ({ ...current, [field]: "Save failed" }));
    } finally {
      setSavingField(null);
    }
  }

  function addTag() {
    const value = tagInput.trim();
    if (!value || tags.includes(value) || tags.length >= 13) {
      setTagInput("");
      return;
    }
    const nextTags = [...tags, value];
    setTags(nextTags);
    setTagInput("");
    void saveCopyField("tags", nextTags);
  }

  function removeTag(tag: string) {
    const nextTags = tags.filter((item) => item !== tag);
    setTags(nextTags);
    void saveCopyField("tags", nextTags);
  }

  function onTagKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      event.preventDefault();
      addTag();
    }
  }

  async function toggleBundle() {
    if (!listingId) return;
    const nextValue = !isBundle;
    setIsBundle(nextValue);
    try {
      await apiFetch<SuccessResponse>(`/listings/${listingId}/bundle`, {
        method: "PATCH",
        json: { is_bundle: nextValue }
      });
      setListingPackage((current) => current ? { ...current, is_bundle: nextValue } : current);
    } catch {
      setIsBundle(!nextValue);
      toast.error("Save failed");
    }
  }

  function uploadToEtsy() {
    if (listingId && uploadReady) {
      router.push(`/new-listing/upload?listing_id=${listingId}`);
    }
  }

  if (loadingPackage) {
    return (
      <Card className="flex min-h-80 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-primary" aria-hidden="true" />
      </Card>
    );
  }

  if (loadError) {
    return (
      <Card className="max-w-xl space-y-4">
        <h1 className="text-xl font-bold text-gray-950">Package Review</h1>
        <p className="text-sm text-gray-600">{loadError}</p>
        <Button type="button" onClick={() => loadPackage()} icon={<RefreshCw className="h-4 w-4" />}>
          Retry
        </Button>
      </Card>
    );
  }

  return (
    <div className="space-y-6 pb-28">
      <div>
        <h1 className="text-2xl font-bold text-gray-950">Package Review</h1>
        <p className="mt-1 text-sm text-gray-600">Images, video, and copy for this listing.</p>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_460px]">
        <div className="space-y-5">
          <Card>
            <div className="relative overflow-hidden rounded-lg border border-gray-100 bg-gray-100">
              {currentImage ? (
                <img src={currentImage} alt={title || "Listing image"} className="aspect-square w-full object-cover" />
              ) : (
                <div className="flex aspect-square items-center justify-center text-sm font-medium text-gray-500">
                  No images available
                </div>
              )}
              {images.length > 1 ? (
                <>
                  <button
                    type="button"
                    className="absolute left-3 top-1/2 flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 text-gray-800 shadow-sm"
                    onClick={previousImage}
                    aria-label="Previous image"
                  >
                    <ChevronLeft className="h-5 w-5" />
                  </button>
                  <button
                    type="button"
                    className="absolute right-3 top-1/2 flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 text-gray-800 shadow-sm"
                    onClick={nextImage}
                    aria-label="Next image"
                  >
                    <ChevronRight className="h-5 w-5" />
                  </button>
                </>
              ) : null}
            </div>
            {images.length > 1 ? (
              <div className="mt-4 flex justify-center gap-2">
                {images.map((imageUrl, index) => (
                  <button
                    key={imageUrl}
                    type="button"
                    className={cn(
                      "h-2.5 w-2.5 rounded-full",
                      index === imageIndex ? "bg-primary" : "bg-gray-300"
                    )}
                    onClick={() => setImageIndex(index)}
                    aria-label={`Show image ${index + 1}`}
                  />
                ))}
              </div>
            ) : null}
          </Card>

          {listingPackage?.pdf_url ? (
            <Card className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-md bg-indigo-50 text-primary">
                  <FileText className="h-5 w-5" aria-hidden="true" />
                </div>
                <div>
                  <h2 className="text-base font-semibold text-gray-950">Digital PDF</h2>
                  <p className="mt-1 text-sm text-gray-500">This file will be uploaded as the Etsy digital download.</p>
                </div>
              </div>
              <a
                href={listingPackage.pdf_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex min-h-10 items-center justify-center gap-2 rounded-md border border-gray-200 bg-white px-4 text-sm font-semibold text-gray-900 transition hover:bg-gray-50"
              >
                <Download className="h-4 w-4" aria-hidden="true" />
                Download PDF
              </a>
            </Card>
          ) : null}

          <Card>
            <div className="mb-4 flex items-center justify-between gap-3">
              <h2 className="text-base font-semibold text-gray-950">Listing Video</h2>
              {videoReady ? <Badge tone="green">Ready</Badge> : <Badge>Optional</Badge>}
            </div>
            {listingPackage?.video_url ? (
              <video
                className="aspect-square w-full rounded-lg bg-black object-cover"
                src={listingPackage.video_url}
                autoPlay
                loop
                muted
                playsInline
                controls
              />
            ) : canUseVideo(plan) || plan === null ? (
              <div className="space-y-4 rounded-lg border border-dashed border-gray-300 bg-gray-50 p-5">
                <div className="flex items-center gap-3 text-sm font-medium text-gray-700">
                  <Film className="h-5 w-5 text-primary" />
                  Video package
                </div>
                {videoLoading ? (
                  <div className="space-y-3">
                    <div className="h-2 overflow-hidden rounded-full bg-gray-200">
                      <div
                        className="h-full rounded-full bg-primary transition-all"
                        style={{ width: `${videoProgress}%` }}
                      />
                    </div>
                    <p className="text-sm text-gray-500">Creating your video package...</p>
                  </div>
                ) : (
                  <div className="flex flex-wrap items-center gap-3">
                    <Button type="button" onClick={generateVideo} icon={<Film className="h-4 w-4" />}>
                      Generate Video
                    </Button>
                    <span className="text-sm font-medium text-gray-500">(costs 10 credits)</span>
                  </div>
                )}
              </div>
            ) : (
              <div className="relative overflow-hidden rounded-lg border border-gray-200 bg-gray-100 p-8">
                <div className="absolute inset-0 bg-white/50 backdrop-blur-sm" />
                <div className="relative mx-auto max-w-sm space-y-3 text-center">
                  <Film className="mx-auto h-8 w-8 text-gray-500" />
                  <p className="text-sm font-semibold text-gray-900">Video generation requires Pro plan.</p>
                  <Button type="button" onClick={() => setUpgradeModalOpen(true)}>
                    Upgrade to Pro
                  </Button>
                </div>
              </div>
            )}
          </Card>

          <Card className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-base font-semibold text-gray-950">This is a bundle</h2>
              <p className="mt-1 text-sm text-gray-500">{isBundle ? "Bundle" : "Single listing"}</p>
            </div>
            <button
              type="button"
              className={cn(
                "relative h-7 w-12 rounded-full transition",
                isBundle ? "bg-primary" : "bg-gray-300"
              )}
              onClick={toggleBundle}
              aria-pressed={isBundle}
              aria-label="Toggle bundle"
            >
              <span
                className={cn(
                  "absolute top-1 h-5 w-5 rounded-full bg-white transition",
                  isBundle ? "left-6" : "left-1"
                )}
              />
            </button>
          </Card>
        </div>

        <Card className="space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-base font-semibold text-gray-950">Listing Copy</h2>
            <div className="flex gap-2">
              <Button
                type="button"
                variant={copyReady ? "secondary" : "primary"}
                loading={copyLoading}
                onClick={generateCopy}
                icon={copyReady ? <RefreshCw className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
              >
                {copyReady ? "Regenerate Copy" : "Generate Copy"}
              </Button>
              <span className="self-center text-sm font-medium text-gray-500">(costs 2 credits)</span>
            </div>
          </div>
          {copyLoading ? (
            <div className="rounded-lg border border-indigo-100 bg-indigo-50 px-4 py-3 text-sm font-medium text-indigo-800">
              Claude is writing your listing copy...
            </div>
          ) : null}

          <label className="block" htmlFor="copy-title">
            <div className="mb-2 flex items-center justify-between gap-3">
              <span className="text-sm font-medium text-gray-800">Title</span>
              <span className={cn("text-xs font-semibold", titleTooLong ? "text-red-600" : "text-gray-500")}>
                {title.length}/140
              </span>
            </div>
            <input
              id="copy-title"
              className={cn(
                "h-11 w-full rounded-md border bg-white px-3 text-sm outline-none transition focus:ring-2",
                titleTooLong ? "border-red-400 focus:ring-red-100" : "border-gray-200 focus:border-primary focus:ring-indigo-100"
              )}
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              onBlur={() => {
                if (!titleTooLong) void saveCopyField("title", title.trim() || null);
              }}
            />
            {saveErrors.title ? <p className="mt-1 text-xs font-medium text-red-600">{saveErrors.title}</p> : null}
          </label>

          <label className="block" htmlFor="copy-description">
            <div className="mb-2 flex items-center justify-between gap-3">
              <span className="text-sm font-medium text-gray-800">Description</span>
              <span className="text-xs font-semibold text-gray-500">{wordCount} words</span>
            </div>
            <textarea
              id="copy-description"
              className="min-h-64 w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm leading-6 outline-none transition focus:border-primary focus:ring-2 focus:ring-indigo-100"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              onBlur={() => saveCopyField("description", description)}
            />
            {saveErrors.description ? <p className="mt-1 text-xs font-medium text-red-600">{saveErrors.description}</p> : null}
          </label>

          <div>
            <div className="mb-2 flex items-center justify-between gap-3">
              <span className="text-sm font-medium text-gray-800">Tags</span>
              <span className="text-xs font-semibold text-gray-500">{tags.length}/13</span>
            </div>
            <div className="flex gap-2">
              <input
                className="h-11 min-w-0 flex-1 rounded-md border border-gray-200 bg-white px-3 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-indigo-100"
                value={tagInput}
                onChange={(event) => setTagInput(event.target.value)}
                onKeyDown={onTagKeyDown}
                onBlur={addTag}
                disabled={tags.length >= 13}
                placeholder="etsy printable"
              />
              <Button type="button" variant="secondary" onClick={addTag} disabled={tags.length >= 13} icon={<Plus className="h-4 w-4" />}>
                Add
              </Button>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {tags.map((tag) => (
                <Badge key={tag} tone="indigo" className="gap-1">
                  {tag}
                  <button type="button" onClick={() => removeTag(tag)} aria-label={`Remove ${tag}`}>
                    <XCircle className="h-3.5 w-3.5" />
                  </button>
                </Badge>
              ))}
            </div>
            {saveErrors.tags ? <p className="mt-1 text-xs font-medium text-red-600">{saveErrors.tags}</p> : null}
          </div>

          <label className="block" htmlFor="copy-price">
            <span className="mb-2 block text-sm font-medium text-gray-800">Price</span>
            <div className="relative">
              <DollarSign className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input
                id="copy-price"
                className="h-11 w-full rounded-md border border-gray-200 bg-white pl-9 pr-3 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-indigo-100"
                type="number"
                min="0"
                step="0.01"
                value={price}
                onChange={(event) => setPrice(event.target.value)}
                onBlur={() => saveCopyField("price", price.trim() ? Number(price) : null)}
              />
            </div>
            {saveErrors.price ? <p className="mt-1 text-xs font-medium text-red-600">{saveErrors.price}</p> : null}
          </label>

          {savingField ? (
            <p className="flex items-center gap-2 text-xs font-medium text-gray-500">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Saving {savingField}...
            </p>
          ) : null}
        </Card>
      </div>

      <div className="fixed inset-x-0 bottom-0 z-30 border-t border-gray-200 bg-white/95 px-4 py-3 shadow-lg backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <Link
            href="/new-listing"
            className="inline-flex min-h-10 items-center gap-2 rounded-md px-3 text-sm font-semibold text-gray-700 hover:bg-gray-100"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Images
          </Link>

          <div className="flex flex-wrap justify-center gap-2">
            <StatusPill label="Images" ready={imagesReady} />
            <StatusPill label="Video" ready={videoReady} optional />
            <StatusPill label="Copy" ready={copyReady} />
          </div>

          <Button
            type="button"
            disabled={!uploadReady}
            onClick={uploadToEtsy}
            icon={<ArrowRight className="h-4 w-4" />}
          >
            Upload to Etsy
          </Button>
        </div>
      </div>

      <Modal open={upgradeModalOpen} title="Upgrade required" onClose={() => setUpgradeModalOpen(false)}>
        <div className="space-y-4">
          <p className="text-sm leading-6 text-gray-600">Video generation requires Pro plan.</p>
          <Button type="button" onClick={() => router.push("/upgrade")} className="w-full">
            Upgrade to Pro
          </Button>
        </div>
      </Modal>
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

function StatusPill({ label, ready, optional = false }: { label: string; ready: boolean; optional?: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex min-h-9 items-center gap-2 rounded-full border px-3 text-xs font-semibold",
        ready ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-gray-200 bg-gray-50 text-gray-500"
      )}
    >
      <CheckCircle2 className={cn("h-4 w-4", ready ? "animate-pulse" : "")} />
      {label}
      {optional && !ready ? <span className="font-medium">(optional)</span> : null}
    </span>
  );
}
