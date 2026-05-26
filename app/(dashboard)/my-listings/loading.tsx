import { Card } from "@/components/ui/Card";

export default function MyListingsLoading() {
  return (
    <div className="space-y-4">
      {[1, 2, 3].map((item) => <Card key={item} className="h-20 animate-pulse bg-gray-100" />)}
    </div>
  );
}
