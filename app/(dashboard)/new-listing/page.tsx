import { NewListingForm } from "@/components/NewListingForm";

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
      <NewListingForm
        initialProductIdea={searchParams?.product_idea || ""}
        initialTargetPrice={searchParams?.target_price || ""}
        initialProductIdeaIndex={searchParams?.product_idea_index || "0"}
      />
    </div>
  );
}
