"use client";

import { CheckSquare, Loader2, UploadCloud } from "lucide-react";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import toast from "react-hot-toast";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { apiFetch } from "@/lib/api";
import type { BulkQueueResponse, Listing, PaginatedListingsResponse } from "@/lib/types";

export default function BulkListingsPage() {
  return (
    <Suspense
      fallback={(
        <Card className="flex min-h-80 items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </Card>
      )}
    >
      <BulkListingsContent />
    </Suspense>
  );
}

function BulkListingsContent() {
  const searchParams = useSearchParams();
  const preselectedIds = useMemo(
    () => (searchParams.get("listing_ids") || "").split(",").map((item) => item.trim()).filter(Boolean),
    [searchParams]
  );
  const [listings, setListings] = useState<Listing[]>([]);
  const [selected, setSelected] = useState<string[]>(preselectedIds);
  const [accepted, setAccepted] = useState(false);
  const [loading, setLoading] = useState(true);
  const [queueing, setQueueing] = useState(false);
  const [queuedCount, setQueuedCount] = useState<number | null>(null);

  const loadDrafts = useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiFetch<PaginatedListingsResponse>("/listings?status=DRAFT&page=1&per_page=100");
      setListings(response.listings);
      setSelected((current) => {
        const ids = new Set(response.listings.map((listing) => listing.id));
        return current.filter((id) => ids.has(id));
      });
    } catch {
      toast.error("Could not load listings. Please refresh.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDrafts();
  }, [loadDrafts]);

  function toggleListing(id: string) {
    setSelected((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  }

  function toggleAll() {
    setSelected((current) => current.length === listings.length ? [] : listings.map((listing) => listing.id));
  }

  async function queueSelected() {
    if (!accepted) {
      toast.error("You must accept the disclaimer to continue.");
      return;
    }
    if (!selected.length) {
      toast.error("Select listings first");
      return;
    }

    setQueueing(true);
    try {
      const response = await apiFetch<BulkQueueResponse>("/listings/bulk-queue", {
        method: "POST",
        json: { listing_ids: selected, disclaimer_accepted: true }
      });
      setQueuedCount(response.queued_count);
      toast.success(`${response.queued_count} listings queued for upload`);
      await loadDrafts();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not queue listings");
    } finally {
      setQueueing(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-950">Bulk Upload</h1>
        <p className="mt-1 text-sm text-gray-600">Queue draft listings for Etsy upload.</p>
      </div>

      <Card className="space-y-4">
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-900">
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
        <div className="rounded-lg bg-indigo-50 px-4 py-3 text-sm font-semibold text-indigo-800">
          Listings will upload one per minute to keep your account safe.
        </div>
      </Card>

      {queuedCount !== null ? (
        <Card className="border-emerald-200 bg-emerald-50 text-emerald-800">
          <p className="text-sm font-semibold">{queuedCount} listings queued for upload</p>
        </Card>
      ) : null}

      <Card className="p-0">
        <div className="flex items-center justify-between gap-3 border-b border-gray-100 px-5 py-4">
          <button type="button" className="inline-flex items-center gap-2 text-sm font-semibold text-gray-700" onClick={toggleAll}>
            <CheckSquare className="h-4 w-4" />
            Select All
          </button>
          <Button type="button" disabled={!selected.length || !accepted} loading={queueing} onClick={queueSelected} icon={<UploadCloud className="h-4 w-4" />}>
            Queue All Selected
          </Button>
        </div>

        {loading ? (
          <div className="flex min-h-64 items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        ) : listings.length === 0 ? (
          <div className="p-8 text-center text-sm text-gray-500">No draft listings available.</div>
        ) : (
          <div className="divide-y divide-gray-100">
            {listings.map((listing) => {
              const thumbnail = listing.primary_image_url || listing.image_urls[0];
              return (
                <label key={listing.id} className="flex cursor-pointer items-center gap-4 px-5 py-4 hover:bg-gray-50">
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                    checked={selected.includes(listing.id)}
                    onChange={() => toggleListing(listing.id)}
                  />
                  <div className="h-14 w-14 overflow-hidden rounded-md bg-gray-100">
                    {thumbnail ? <img src={thumbnail} alt={listing.title || "Listing thumbnail"} className="h-full w-full object-cover" /> : null}
                  </div>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-gray-950">{listing.title || "Untitled listing"}</p>
                    <p className="mt-1 text-xs text-gray-500">{listing.id}</p>
                  </div>
                </label>
              );
            })}
          </div>
        )}
      </Card>
    </div>
  );
}
