"use client";

import { Calendar, Download, ExternalLink, Loader2, RefreshCw, Trash2, UploadCloud } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Listing, PaginatedListingsResponse, SuccessResponse } from "@/lib/types";

type StatusFilter = "ALL" | Listing["status"];

const filters: { label: string; value: StatusFilter }[] = [
  { label: "All", value: "ALL" },
  { label: "Draft", value: "DRAFT" },
  { label: "Queued", value: "QUEUED" },
  { label: "Live", value: "LIVE" },
  { label: "Failed", value: "FAILED" }
];

function statusClass(status: Listing["status"]) {
  if (status === "LIVE") return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (status === "FAILED") return "border-red-200 bg-red-50 text-red-700";
  if (status === "QUEUED") return "animate-pulse border-sky-200 bg-sky-50 text-sky-700";
  if (status === "QUEUED_MANUAL") return "border-purple-200 bg-purple-50 text-purple-700";
  return "border-gray-200 bg-gray-50 text-gray-700";
}

export default function MyListingsPage() {
  const router = useRouter();
  const [listings, setListings] = useState<Listing[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [filter, setFilter] = useState<StatusFilter>("ALL");
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<string[]>([]);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const totalPages = Math.max(1, Math.ceil(total / 20));
  const selectedDrafts = useMemo(
    () => selected.filter((id) => listings.find((listing) => listing.id === id && listing.status !== "LIVE" && listing.status !== "QUEUED")),
    [listings, selected]
  );

  const loadListings = useCallback(async (nextPage: number, nextFilter: StatusFilter) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: String(nextPage),
        per_page: "20"
      });
      if (nextFilter !== "ALL") {
        params.set("status", nextFilter);
      }
      const response = await apiFetch<PaginatedListingsResponse>(`/listings?${params.toString()}`);
      setListings(response.listings);
      setTotal(response.total);
      setSelected([]);
    } catch {
      toast.error("Could not load listings. Please refresh.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadListings(page, filter);
  }, [filter, loadListings, page]);

  function toggleSelected(id: string) {
    setSelected((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  }

  async function downloadZip(listing: Listing) {
    setDownloadingId(listing.id);
    try {
      const blob = await apiFetch<Blob>(`/listings/${listing.id}/download`, { responseType: "blob" });
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `listing-${listing.id}.zip`;
      anchor.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not create download. Please try again.");
    } finally {
      setDownloadingId(null);
    }
  }

  async function deleteListing(listing: Listing) {
    setDeletingId(listing.id);
    try {
      await apiFetch<SuccessResponse>(`/listings/${listing.id}`, { method: "DELETE" });
      toast.success("Listing deleted");
      await loadListings(page, filter);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Cannot delete a listing that is currently uploading.");
    } finally {
      setDeletingId(null);
    }
  }

  function queueSelected() {
    if (!selectedDrafts.length) {
      toast.error("Select listings first");
      return;
    }
    router.push(`/bulk-listings?listing_ids=${selectedDrafts.join(",")}`);
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-950">My Listings</h1>
          <p className="mt-1 text-sm text-gray-600">Generated listing packages and Etsy upload status.</p>
        </div>
        <Button type="button" disabled={!selectedDrafts.length} onClick={queueSelected} icon={<UploadCloud className="h-4 w-4" />}>
          Queue Selected for Upload
        </Button>
      </div>

      <div className="flex flex-wrap gap-2">
        {filters.map((item) => (
          <button
            key={item.value}
            type="button"
            className={cn(
              "min-h-10 rounded-md border px-4 text-sm font-semibold transition",
              filter === item.value ? "border-primary bg-indigo-50 text-primary" : "border-gray-200 bg-white text-gray-600 hover:bg-gray-50"
            )}
            onClick={() => {
              setPage(1);
              setFilter(item.value);
            }}
          >
            {item.label}
          </button>
        ))}
      </div>

      <Card className="p-0">
        {loading ? (
          <div className="flex min-h-64 items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        ) : listings.length === 0 ? (
          <div className="p-8 text-center text-sm text-gray-500">No listings found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[920px] border-collapse text-left">
              <thead>
                <tr className="border-b border-gray-100 text-xs uppercase text-gray-500">
                  <th className="w-12 px-4 py-3" />
                  <th className="px-4 py-3">Listing</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Created</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {listings.map((listing) => {
                  const thumbnail = listing.primary_image_url || listing.image_urls[0];
                  const etsyUrl = listing.etsy_listing_id ? `https://www.etsy.com/listing/${listing.etsy_listing_id}` : null;
                  const canDelete = listing.status !== "QUEUED" && listing.status !== "LIVE";
                  return (
                    <tr key={listing.id} className="border-b border-gray-100 last:border-0">
                      <td className="px-4 py-4">
                        <input
                          type="checkbox"
                          className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                          checked={selected.includes(listing.id)}
                          onChange={() => toggleSelected(listing.id)}
                        />
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-3">
                          <div className="h-14 w-14 overflow-hidden rounded-md bg-gray-100">
                            {thumbnail ? (
                              <img src={thumbnail} alt={listing.title || "Listing thumbnail"} className="h-full w-full object-cover" />
                            ) : null}
                          </div>
                          <div className="min-w-0">
                            <p className="max-w-sm truncate text-sm font-semibold text-gray-950">{listing.title || "Untitled listing"}</p>
                            <p className="mt-1 text-xs text-gray-500">{listing.id}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <span className={cn("inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold", statusClass(listing.status))}>
                          {listing.status}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-sm text-gray-500">
                        <span className="inline-flex items-center gap-2">
                          <Calendar className="h-4 w-4" />
                          {new Date(listing.created_at).toLocaleDateString()}
                        </span>
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex justify-end gap-2">
                          {etsyUrl ? (
                            <a
                              href={etsyUrl}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex min-h-10 items-center gap-2 rounded-md border border-gray-200 bg-white px-3 text-sm font-semibold text-gray-700 hover:bg-gray-50"
                            >
                              <ExternalLink className="h-4 w-4" />
                              View on Etsy
                            </a>
                          ) : null}
                          {listing.status === "FAILED" ? (
                            <Button type="button" variant="secondary" onClick={() => router.push(`/new-listing/upload?listing_id=${listing.id}`)} icon={<RefreshCw className="h-4 w-4" />}>
                              Retry
                            </Button>
                          ) : null}
                          <Button type="button" variant="secondary" loading={downloadingId === listing.id} onClick={() => downloadZip(listing)} icon={<Download className="h-4 w-4" />}>
                            ZIP
                          </Button>
                          {canDelete ? (
                            <Button type="button" variant="ghost" loading={deletingId === listing.id} onClick={() => deleteListing(listing)} icon={<Trash2 className="h-4 w-4" />}>
                              Delete
                            </Button>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <div className="flex items-center justify-between gap-3">
        <Button type="button" variant="secondary" disabled={page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>
          Previous
        </Button>
        <span className="text-sm font-medium text-gray-500">Page {page} of {totalPages}</span>
        <Button type="button" variant="secondary" disabled={page >= totalPages} onClick={() => setPage((current) => current + 1)}>
          Next
        </Button>
      </div>
    </div>
  );
}
