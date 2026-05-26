import { Card } from "@/components/ui/Card";

export default function ShopAnalysisLoading() {
  return (
    <div className="space-y-4">
      <Card className="h-24 animate-pulse bg-gray-100" />
      <div className="grid gap-4 md:grid-cols-3">
        {[1, 2, 3].map((item) => <Card key={item} className="h-40 animate-pulse bg-gray-100" />)}
      </div>
    </div>
  );
}
