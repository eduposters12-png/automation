import { Calendar, ImageIcon } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { getListings } from "@/lib/server-api";

function statusTone(status: string): "gray" | "green" | "red" | "amber" {
  if (status === "LIVE") return "green";
  if (status === "FAILED") return "red";
  if (status === "QUEUED") return "amber";
  return "gray";
}

export default async function ListingsPage() {
  const response = await getListings();
  const listings = response?.listings || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-950">My Listings</h1>
        <p className="mt-1 text-sm text-gray-600">Generated listing records and upload status.</p>
      </div>

      {listings.length === 0 ? (
        <Card className="text-center">
          <ImageIcon className="mx-auto h-10 w-10 text-gray-300" aria-hidden="true" />
          <h2 className="mt-4 text-base font-semibold text-gray-950">No listings yet</h2>
          <p className="mt-1 text-sm text-gray-600">Queue your first listing workflow from New Listing.</p>
        </Card>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <div className="min-w-[620px]">
            <div className="grid grid-cols-[1fr_120px_140px] gap-4 border-b border-gray-100 px-4 py-3 text-xs font-semibold uppercase text-gray-500">
              <span>Listing</span>
              <span>Status</span>
              <span>Created</span>
            </div>
            {listings.map((listing) => (
              <div
                key={listing.id}
                className="grid grid-cols-[1fr_120px_140px] gap-4 border-b border-gray-100 px-4 py-4 last:border-0"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-gray-950">{listing.title || "Untitled listing"}</p>
                  <p className="mt-1 truncate text-xs text-gray-500">{listing.etsy_listing_id || listing.id}</p>
                </div>
                <Badge tone={statusTone(listing.status)}>{listing.status}</Badge>
                <div className="flex items-center gap-2 text-sm text-gray-500">
                  <Calendar className="h-4 w-4" aria-hidden="true" />
                  {new Date(listing.created_at).toLocaleDateString()}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
