import { NewListingForm } from "@/components/NewListingForm";

export default function NewListingPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-950">New Listing</h1>
        <p className="mt-1 text-sm text-gray-600">Queue a generation workflow for the connected Etsy shop.</p>
      </div>
      <NewListingForm />
    </div>
  );
}
