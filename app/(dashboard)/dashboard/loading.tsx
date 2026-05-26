import { Card } from "@/components/ui/Card";

export default function DashboardLoading() {
  return (
    <div className="grid gap-4 lg:grid-cols-4">
      {[1, 2, 3, 4].map((item) => <Card key={item} className="h-28 animate-pulse bg-gray-100" />)}
    </div>
  );
}
