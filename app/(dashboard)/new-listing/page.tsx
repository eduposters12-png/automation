import { ArrowRight, FileText } from "lucide-react";
import Link from "next/link";

import { NewListingForm } from "@/components/NewListingForm";
import { Card } from "@/components/ui/Card";

export default function NewListingPage({
  searchParams
}: {
  searchParams?: { product_idea?: string; product_idea_index?: string; target_price?: string };
}) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-950">New Listing</h1>
        <p className="mt-1 text-sm text-gray-600">Queue a generation workflow for the connected Etsy shop.</p>
      </div>
      <Card className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-indigo-50 text-primary">
            <FileText className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-gray-950">Multi-Page Digital Product</h2>
            <p className="mt-1 text-sm leading-6 text-gray-600">
              Let Claude plan and generate a complete multi-page PDF product (posters, books, flashcards).
            </p>
          </div>
        </div>
        <Link
          href="/new-listing/multi-page"
          className="inline-flex min-h-10 shrink-0 items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-semibold text-white transition hover:bg-indigo-500"
        >
          Start -&gt;
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </Link>
      </Card>
      <NewListingForm
        initialProductIdea={searchParams?.product_idea || ""}
        initialTargetPrice={searchParams?.target_price || ""}
        initialProductIdeaIndex={searchParams?.product_idea_index || "0"}
      />
    </div>
  );
}
