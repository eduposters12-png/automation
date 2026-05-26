"use client";

import {
  ArrowRight,
  ArrowUp,
  Check,
  GripVertical,
  ImageIcon,
  Loader2,
  Plus,
  RefreshCw,
  Sparkles,
  Trash2,
  Wand2,
  X
} from "lucide-react";
import Link from "next/link";
import { FormEvent, KeyboardEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { InsufficientCreditsModal } from "@/components/InsufficientCreditsModal";
import { ApiError, apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";
import type {
  ApproveImageResponse,
  AuthResponse,
  ClaudeImageReview,
  HighResImageResponse,
  ImageGenerationResponse,
  Plan,
  RegenerateImageResponse
} from "@/lib/types";

type NewListingFormProps = {
  initialProductIdea?: string;
  initialTargetPrice?: string;
  initialProductIdeaIndex?: string;
};

type Step = 1 | 2 | 3;

const generationSteps = [
  "Building your image prompt...",
  "GPT-4o is creating your image...",
  "Claude is reviewing the result..."
];

const emptyReview: ClaudeImageReview = {
  approved: false,
  feedback: "",
  improvedPrompt: ""
};

function parseProductIndex(value: string) {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : 0;
}

function imageLimit(plan: Plan | null) {
  if (plan === "BASIC") return 3;
  if (plan === "PRO") return 10;
  if (plan === "FREE") return 0;
  return null;
}

export function NewListingForm({
  initialProductIdea = "",
  initialTargetPrice = "",
  initialProductIdeaIndex = "0"
}: NewListingFormProps) {
  const router = useRouter();
  const [step, setStep] = useState<Step>(1);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [productIdeaIndex] = useState(() => parseProductIndex(initialProductIdeaIndex));
  const [title, setTitle] = useState(initialProductIdea);
  const [keywords, setKeywords] = useState<string[]>([]);
  const [keywordInput, setKeywordInput] = useState("");
  const [styleNotes, setStyleNotes] = useState("");
  const [estimatedPrice, setEstimatedPrice] = useState(initialTargetPrice);
  const [listingId, setListingId] = useState<string | null>(null);
  const [imageUrls, setImageUrls] = useState<string[]>([]);
  const [currentImageUrl, setCurrentImageUrl] = useState<string | null>(null);
  const [approvedImageUrl, setApprovedImageUrl] = useState<string | null>(null);
  const [review, setReview] = useState<ClaudeImageReview>(emptyReview);
  const [loadingAction, setLoadingAction] = useState<string | null>(null);
  const [activeLoadingStep, setActiveLoadingStep] = useState(0);
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [upgradeModal, setUpgradeModal] = useState<{ title: string; message: string } | null>(null);
  const [insufficientCredits, setInsufficientCredits] = useState<{ required: number; balance: number; action: string } | null>(null);

  const maxImages = useMemo(() => imageLimit(plan), [plan]);
  const imageWorking = ["generate", "regenerate", "improve", "high-res", "add"].includes(loadingAction || "");
  const imageCountText = maxImages === null ? `Image ${imageUrls.length}` : `Image ${imageUrls.length} of ${maxImages}`;

  useEffect(() => {
    async function loadPlan() {
      try {
        const auth = await apiFetch<AuthResponse>("/auth/me");
        setPlan(auth.user.plan);
      } catch {
        setPlan(null);
      }
    }

    void loadPlan();
  }, []);

  useEffect(() => {
    if (!imageWorking) return undefined;
    const interval = window.setInterval(() => {
      setActiveLoadingStep((current) => Math.min(current + 1, generationSteps.length - 1));
    }, 1600);
    return () => window.clearInterval(interval);
  }, [imageWorking]);

  function payload(isHighRes: boolean, includeListing = false) {
    return {
      product_idea_index: productIdeaIndex,
      is_high_res: isHighRes,
      product_title: title,
      keywords,
      style_notes: styleNotes,
      estimated_price: estimatedPrice.trim() ? estimatedPrice : undefined,
      listing_id: includeListing ? listingId : undefined
    };
  }

  function showPlanModal(titleText: string, message: string) {
    setUpgradeModal({ title: titleText, message });
  }

  function showRetryToast(message: string, retry: () => Promise<void>) {
    toast.custom((toastInstance) => (
      <div className="flex max-w-md items-center gap-3 rounded-lg border border-gray-200 bg-white px-4 py-3 text-sm shadow-soft">
        <span className="min-w-0 flex-1 text-gray-700">{message}</span>
        <button
          type="button"
          className="shrink-0 font-semibold text-primary"
          onClick={() => {
            toast.dismiss(toastInstance.id);
            void retry();
          }}
        >
          Retry
        </button>
      </div>
    ));
  }

  function handleApiError(error: unknown, retry: () => Promise<void>, fallback: string) {
    if (error instanceof ApiError && error.code === "INSUFFICIENT_CREDITS") {
      setInsufficientCredits({
        required: Number(error.detail?.required || 0),
        balance: Number(error.detail?.balance || 0),
        action: String(error.detail?.action || "")
      });
      return;
    }
    const message = error instanceof Error ? error.message : fallback;
    if (message.includes("Upgrade") || message.includes("Pro plan") || message.includes("limit")) {
      showPlanModal("Upgrade required", message);
      return;
    }
    showRetryToast(message, retry);
  }

  function applyGeneratedImage(response: ImageGenerationResponse | RegenerateImageResponse) {
    setImageUrls(response.image_urls);
    setCurrentImageUrl(response.image_url);
    setReview(response.claude_review);
    if (response.review_unavailable) {
      toast("Image generated, but Claude review is unavailable.", { icon: "!" });
    }
  }

  function addKeyword() {
    const keyword = keywordInput.trim();
    if (!keyword || keywords.includes(keyword) || keywords.length >= 13) {
      setKeywordInput("");
      return;
    }
    setKeywords((current) => [...current, keyword]);
    setKeywordInput("");
  }

  function onKeywordKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      event.preventDefault();
      addKeyword();
    }
  }

  function removeKeyword(keyword: string) {
    setKeywords((current) => current.filter((item) => item !== keyword));
  }

  async function generateImage(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    if (plan === "FREE") {
      showPlanModal("Upgrade required", "Upgrade your plan to generate images.");
      return;
    }

    setStep(2);
    setLoadingAction("generate");
    setActiveLoadingStep(0);
    try {
      const response = await apiFetch<ImageGenerationResponse>("/listings/generate-image", {
        method: "POST",
        json: payload(false)
      });
      setListingId(response.listing_id);
      applyGeneratedImage(response);
      toast.success("Image generated");
    } catch (error) {
      handleApiError(error, () => generateImage(), "Image generation failed. Please try again.");
    } finally {
      setLoadingAction(null);
    }
  }

  async function regenerateImage(useImprovedPrompt: boolean) {
    if (!listingId) return;
    setLoadingAction(useImprovedPrompt ? "improve" : "regenerate");
    setActiveLoadingStep(0);
    try {
      const response = await apiFetch<RegenerateImageResponse>(`/listings/${listingId}/regenerate-image`, {
        method: "POST",
        json: { use_improved_prompt: useImprovedPrompt }
      });
      applyGeneratedImage(response);
      toast.success("Image regenerated");
    } catch (error) {
      handleApiError(error, () => regenerateImage(useImprovedPrompt), "Image generation failed. Please try again.");
    } finally {
      setLoadingAction(null);
    }
  }

  async function generateHighRes() {
    if (!listingId) return;
    if (plan === "BASIC" || plan === "FREE") {
      showPlanModal("High resolution requires Pro", "High resolution requires Pro plan.");
      return;
    }

    setLoadingAction("high-res");
    setActiveLoadingStep(0);
    try {
      const response = await apiFetch<HighResImageResponse>(`/listings/${listingId}/set-high-res`, {
        method: "POST"
      });
      setImageUrls(response.image_urls);
      setCurrentImageUrl(response.image_url);
      toast.success("High resolution image generated");
    } catch (error) {
      handleApiError(error, generateHighRes, "Image generation failed. Please try again.");
    } finally {
      setLoadingAction(null);
    }
  }

  async function approveCurrentImage() {
    if (!currentImageUrl) return;
    await approveImageUrl(currentImageUrl);
  }

  async function approveImageUrl(imageUrl: string) {
    if (!listingId) return;
    setLoadingAction("approve");
    try {
      await apiFetch<ApproveImageResponse>(`/listings/${listingId}/approve-image`, {
        method: "PATCH",
        json: { approved_image_url: imageUrl }
      });
      setApprovedImageUrl(imageUrl);
      setStep(3);
      toast.success("Image approved");
    } catch (error) {
      handleApiError(error, () => approveImageUrl(imageUrl), "Could not approve image. Please try again.");
    } finally {
      setLoadingAction(null);
    }
  }

  async function addAnotherImage() {
    if (!listingId) return;
    if (maxImages !== null && imageUrls.length >= maxImages) {
      showPlanModal("Upgrade required", "Image limit reached for your plan.");
      return;
    }

    setLoadingAction("add");
    setActiveLoadingStep(0);
    try {
      const response = await apiFetch<ImageGenerationResponse>("/listings/generate-image", {
        method: "POST",
        json: payload(false, true)
      });
      applyGeneratedImage(response);
      toast.success("Image added");
    } catch (error) {
      handleApiError(error, addAnotherImage, "Image generation failed. Please try again.");
    } finally {
      setLoadingAction(null);
    }
  }

  function deleteLocalImage(imageUrl: string) {
    const nextImages = imageUrls.filter((url) => url !== imageUrl);
    setImageUrls(nextImages);
    if (currentImageUrl === imageUrl) {
      setCurrentImageUrl(nextImages.at(-1) || null);
    }
    if (approvedImageUrl === imageUrl) {
      setApprovedImageUrl(null);
    }
  }

  function onDropImage(targetIndex: number) {
    if (dragIndex === null || dragIndex === targetIndex) {
      setDragIndex(null);
      return;
    }
    setImageUrls((current) => {
      const next = [...current];
      const [moved] = next.splice(dragIndex, 1);
      next.splice(targetIndex, 0, moved);
      return next;
    });
    setDragIndex(null);
  }

  const reviewApproved = review.approved;
  const history = imageUrls.slice(-3).reverse();
  const canContinue = Boolean(listingId && approvedImageUrl && imageUrls.includes(approvedImageUrl));

  return (
    <div className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-3">
        {[1, 2, 3].map((stepNumber) => (
          <div
            key={stepNumber}
            className={cn(
              "rounded-lg border px-4 py-3 text-sm font-semibold",
              step === stepNumber ? "border-primary bg-indigo-50 text-primary" : "border-gray-200 bg-white text-gray-500"
            )}
          >
            Step {stepNumber} of 3
          </div>
        ))}
      </div>

      {step === 1 ? (
        <Card className="max-w-3xl">
          <form className="space-y-5" onSubmit={generateImage}>
            <Input
              label="Product title"
              name="product_title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              required
              minLength={3}
            />
            <div>
              <label className="block text-sm font-medium text-gray-800" htmlFor="keyword-input">
                Keywords
              </label>
              <div className="mt-2 flex gap-2">
                <input
                  id="keyword-input"
                  className="h-11 min-w-0 flex-1 rounded-md border border-gray-200 px-3 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-indigo-100"
                  value={keywordInput}
                  onChange={(event) => setKeywordInput(event.target.value)}
                  onKeyDown={onKeywordKeyDown}
                  placeholder="printable planner"
                />
                <Button type="button" variant="secondary" onClick={addKeyword} icon={<Plus className="h-4 w-4" />}>
                  Add
                </Button>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {keywords.map((keyword) => (
                  <Badge key={keyword} tone="indigo" className="gap-1">
                    {keyword}
                    <button type="button" onClick={() => removeKeyword(keyword)} aria-label={`Remove ${keyword}`}>
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            </div>
            <label className="block" htmlFor="style-notes">
              <span className="mb-2 block text-sm font-medium text-gray-800">Style notes</span>
              <textarea
                id="style-notes"
                className="min-h-28 w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm text-gray-950 outline-none transition placeholder:text-gray-400 focus:border-primary focus:ring-2 focus:ring-indigo-100"
                value={styleNotes}
                onChange={(event) => setStyleNotes(event.target.value)}
                placeholder="Minimal, premium, neutral colors, soft shadows"
              />
            </label>
            <Input
              label="Estimated price"
              name="estimated_price"
              type="number"
              min="0"
              step="0.01"
              value={estimatedPrice}
              onChange={(event) => setEstimatedPrice(event.target.value)}
            />
            <div className="flex flex-wrap items-center gap-3">
              <Button type="submit" loading={loadingAction === "generate"} icon={<Sparkles className="h-4 w-4" />}>
                Generate Image
              </Button>
              <span className="text-sm font-medium text-gray-500">(costs 5 credits)</span>
            </div>
          </form>
        </Card>
      ) : null}

      {step === 2 ? (
        imageWorking ? (
          <Card className="space-y-4">
            {generationSteps.map((label, index) => (
              <div key={label} className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-50 text-primary">
                  {index === activeLoadingStep ? <Loader2 className="h-4 w-4 animate-spin" /> : index + 1}
                </div>
                <span className={cn("text-sm font-medium", index === activeLoadingStep ? "text-gray-950" : "text-gray-500")}>
                  {label}
                </span>
              </div>
            ))}
          </Card>
        ) : currentImageUrl ? (
          <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
            <Card>
              <div className="mx-auto max-w-2xl overflow-hidden rounded-lg border border-gray-100 bg-gray-50">
                <img src={currentImageUrl} alt={title || "Generated product image"} className="aspect-square w-full object-cover" />
              </div>
              <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
                <span className="text-sm font-semibold text-gray-500">{imageCountText}</span>
                <div className="flex flex-wrap gap-2">
                  <Button type="button" onClick={approveCurrentImage} loading={loadingAction === "approve"} icon={<Check className="h-4 w-4" />}>
                    Use This Image
                  </Button>
                  <Button type="button" variant="secondary" onClick={() => regenerateImage(false)} icon={<RefreshCw className="h-4 w-4" />}>
                    Regenerate
                  </Button>
                  <span className="self-center text-xs font-semibold text-gray-500">(5 credits)</span>
                  <Button type="button" variant="secondary" onClick={() => regenerateImage(true)} icon={<Wand2 className="h-4 w-4" />}>
                    Apply Claude&apos;s Suggestion
                  </Button>
                  <span className="self-center text-xs font-semibold text-gray-500">(5 credits)</span>
                  <Button type="button" variant="secondary" onClick={generateHighRes} icon={<ArrowUp className="h-4 w-4" />}>
                    High Resolution
                  </Button>
                  <span className="self-center text-xs font-semibold text-gray-500">(8 credits)</span>
                </div>
              </div>
            </Card>
            <div className="space-y-5">
              <Card>
                <div className="flex items-center justify-between gap-3">
                  <h2 className="text-base font-semibold text-gray-950">Claude Review</h2>
                  <Badge tone={reviewApproved ? "green" : "amber"}>{reviewApproved ? "Looks Great!" : "Needs Improvement"}</Badge>
                </div>
                <div className="mt-4 border-l-4 border-indigo-300 bg-indigo-50 px-4 py-3 text-sm leading-6 text-indigo-900">
                  {review.feedback || "Review unavailable"}
                </div>
              </Card>
              <Card>
                <h2 className="text-base font-semibold text-gray-950">Image history</h2>
                <div className="mt-4 grid grid-cols-3 gap-3">
                  {history.map((url) => (
                    <button
                      key={url}
                      type="button"
                      className={cn(
                        "overflow-hidden rounded-md border bg-gray-50",
                        currentImageUrl === url ? "border-primary ring-2 ring-indigo-100" : "border-gray-200"
                      )}
                      onClick={() => setCurrentImageUrl(url)}
                    >
                      <img src={url} alt="Generated thumbnail" className="aspect-square w-full object-cover" />
                    </button>
                  ))}
                </div>
              </Card>
            </div>
          </div>
        ) : null
      ) : null}

      {step === 3 ? (
        <div className="space-y-5">
          <Card className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-base font-semibold text-gray-950">Multi-Image Mode</h2>
              <p className="mt-1 text-sm text-gray-500">{imageCountText}</p>
            </div>
            <Button type="button" onClick={addAnotherImage} loading={loadingAction === "add"} icon={<Plus className="h-4 w-4" />}>
              Add Another Image
            </Button>
            <span className="text-sm font-medium text-gray-500">(costs 5 credits)</span>
          </Card>

          {loadingAction === "add" ? (
            <Card className="flex min-h-36 items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </Card>
          ) : null}

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {imageUrls.map((url, index) => (
              <Card
                key={url}
                className="p-3"
                draggable
                onDragStart={() => setDragIndex(index)}
                onDragOver={(event) => event.preventDefault()}
                onDrop={() => onDropImage(index)}
              >
                <div className="relative overflow-hidden rounded-md bg-gray-50">
                  <img src={url} alt={`Product image ${index + 1}`} className="aspect-square w-full object-cover" />
                  {approvedImageUrl === url ? (
                    <Badge tone="green" className="absolute left-3 top-3">
                      Approved
                    </Badge>
                  ) : null}
                </div>
                <div className="mt-3 flex items-center justify-between gap-2">
                  <button type="button" className="flex items-center gap-2 text-sm font-medium text-gray-500">
                    <GripVertical className="h-4 w-4" />
                    Drag
                  </button>
                  <div className="flex gap-2">
                    <Button type="button" variant="secondary" onClick={() => approveImageUrl(url)} icon={<Check className="h-4 w-4" />}>
                      Approve
                    </Button>
                    <Button type="button" variant="ghost" onClick={() => deleteLocalImage(url)} icon={<Trash2 className="h-4 w-4" />}>
                      Delete
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>

          <div className="flex justify-end">
            {canContinue && listingId ? (
              <Link
                href={`/new-listing/package?listing_id=${listingId}`}
                className="inline-flex min-h-10 items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-semibold text-white transition hover:bg-indigo-500"
              >
                Review Listing Package
                <ArrowRight className="h-4 w-4" />
              </Link>
            ) : (
              <Button type="button" disabled icon={<ImageIcon className="h-4 w-4" />}>
                Approve an image to continue
              </Button>
            )}
          </div>
        </div>
      ) : null}

      <Modal open={Boolean(upgradeModal)} title={upgradeModal?.title || "Upgrade required"} onClose={() => setUpgradeModal(null)}>
        <div className="space-y-4">
          <p className="text-sm leading-6 text-gray-600">{upgradeModal?.message}</p>
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
