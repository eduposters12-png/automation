"use client";

import * as Sentry from "@sentry/nextjs";
import { BarChart3, ListChecks, PlusCircle, Sparkles, Store } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { Suspense, useEffect, useState, type ReactNode } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import toast from "react-hot-toast";

import { NoAnalysisState, NoListingsState } from "@/components/EmptyStates";
import { UsageBar } from "@/components/UsageBar";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Modal } from "@/components/ui/Modal";
import { apiFetch } from "@/lib/api";
import type { AnalyticsDashboard } from "@/lib/types";

const tips = [
  "Use exact buyer keywords in the first half of your title.",
  "Keep mockups clean and readable at thumbnail size.",
  "Refresh shop analysis after major niche or seasonal changes."
];

export default function DashboardPage() {
  return (
    <Suspense fallback={<DashboardLoading />}>
      <DashboardContent />
    </Suspense>
  );
}

function DashboardContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [data, setData] = useState<AnalyticsDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [tipsOpen, setTipsOpen] = useState(false);
  const [welcomeOpen, setWelcomeOpen] = useState(searchParams.get("welcome") === "true");

  useEffect(() => {
    async function loadDashboard() {
      try {
        const response = await apiFetch<AnalyticsDashboard>("/analytics/dashboard");
        setData(response);
      } catch (error) {
        Sentry.captureException(error);
        toast.error("Could not load dashboard");
      } finally {
        setLoading(false);
      }
    }

    void loadDashboard();
  }, []);

  if (loading) return <DashboardLoading />;
  if (!data) return null;

  const imageUsage = data.usage_this_month.IMAGE_GENERATED;
  const videoUsage = data.usage_this_month.VIDEO_GENERATED;
  const uploadUsage = data.usage_this_month.LISTING_UPLOADED;

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-950">Dashboard</h1>
          <p className="mt-1 text-sm text-gray-600">Your Etsy growth command center.</p>
        </div>
        <Badge tone="indigo">{data.plan}</Badge>
      </div>

      <div className="grid gap-4 lg:grid-cols-4">
        <StatCard label="Total Listings Created" value={data.total_listings} icon={<ListChecks className="h-6 w-6" />} />
        <StatCard label="Listings Live on Etsy" value={data.live_listings} icon={<Store className="h-6 w-6" />} />
        <Card>
          <UsageBar label="Images" used={imageUsage.used} limit={imageUsage.limit} />
        </Card>
        <Card>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Plan</p>
              <p className="mt-2 text-2xl font-bold text-gray-950">{data.plan}</p>
            </div>
            {data.plan !== "AGENCY" ? (
              <Button type="button" onClick={() => router.push("/upgrade")}>Upgrade</Button>
            ) : null}
          </div>
        </Card>
      </div>

      <div className="grid gap-5 xl:grid-cols-[360px_minmax(0,1fr)_360px]">
        <Card>
          <h2 className="text-base font-semibold text-gray-950">Quick Actions</h2>
          <div className="mt-4 grid gap-2">
            <QuickAction href="/new-listing" icon={<PlusCircle className="h-4 w-4" />} label="New Listing" />
            <QuickAction href="/shop-analysis" icon={<BarChart3 className="h-4 w-4" />} label="Analyze My Shop" />
            <QuickAction href="/my-listings" icon={<ListChecks className="h-4 w-4" />} label="View My Listings" />
            <QuickAction href="/bulk-listings" icon={<Sparkles className="h-4 w-4" />} label="Bulk Generate" />
          </div>
        </Card>

        {data.recent_listings.length ? (
          <Card>
            <h2 className="text-base font-semibold text-gray-950">Recent Activity</h2>
            <div className="mt-4 divide-y divide-gray-100">
              {data.recent_listings.map((listing) => (
                <div key={listing.id} className="flex items-center gap-3 py-3">
                  <div className="relative h-12 w-12 overflow-hidden rounded-md bg-gray-100">
                    {listing.primary_image_url ? (
                      <Image src={listing.primary_image_url} alt={listing.title || "Listing thumbnail"} fill className="object-cover" sizes="48px" />
                    ) : null}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-gray-950">{listing.title || "Untitled listing"}</p>
                    <p className="text-xs text-gray-500">{new Date(listing.created_at).toLocaleDateString()}</p>
                  </div>
                  <Badge>{listing.status}</Badge>
                </div>
              ))}
            </div>
          </Card>
        ) : (
          <NoListingsState />
        )}

        {data.shop.niche ? (
          <Card>
            <h2 className="text-base font-semibold text-gray-950">Shop Health</h2>
            <div className="mt-4 space-y-3 text-sm text-gray-600">
              <p><span className="font-semibold text-gray-950">Niche:</span> {data.shop.niche}</p>
              <p><span className="font-semibold text-gray-950">Last analyzed:</span> {data.shop.last_analyzed_at ? new Date(data.shop.last_analyzed_at).toLocaleString() : "Not yet"}</p>
              <Button type="button" variant="secondary" onClick={() => router.push("/shop-analysis")}>Re-analyze</Button>
            </div>
          </Card>
        ) : (
          <NoAnalysisState />
        )}
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card className="space-y-4">
          <UsageBar label="Videos" used={videoUsage.used} limit={videoUsage.limit} />
          <UsageBar label="Uploads" used={uploadUsage.used} limit={uploadUsage.limit} />
        </Card>
        <Card>
          <button type="button" className="flex w-full items-center justify-between text-left" onClick={() => setTipsOpen((open) => !open)}>
            <span className="text-base font-semibold text-gray-950">Tips for Better Results</span>
            <span className="text-sm font-semibold text-primary">{tipsOpen ? "Hide" : "Show"}</span>
          </button>
          {tipsOpen ? (
            <ul className="mt-4 space-y-2 text-sm text-gray-600">
              {tips.map((tip) => <li key={tip}>{tip}</li>)}
            </ul>
          ) : null}
          <div className="mt-5 flex flex-wrap gap-3 text-sm font-semibold text-primary">
            <a href="https://www.etsy.com/seller-handbook" target="_blank" rel="noreferrer">Etsy Seller Handbook</a>
            <a href="https://www.etsy.com/seller-handbook/category/marketing" target="_blank" rel="noreferrer">Marketing Guides</a>
          </div>
        </Card>
      </div>

      <Modal open={welcomeOpen} title="Welcome to ListifyAI" onClose={() => setWelcomeOpen(false)}>
        <div className="space-y-3 text-sm text-gray-600">
          <p>Your shop analysis is ready. Start with a product idea, generate images, then review your listing package.</p>
          <Button type="button" onClick={() => router.push("/shop-analysis")} className="w-full">View Opportunities</Button>
        </div>
      </Modal>
    </div>
  );
}

function DashboardLoading() {
  return (
    <div className="grid gap-4 lg:grid-cols-4">
      {[1, 2, 3, 4].map((item) => <Card key={item} className="h-28 animate-pulse bg-gray-100" />)}
    </div>
  );
}

function StatCard({ label, value, icon }: { label: string; value: number; icon: ReactNode }) {
  return (
    <Card>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500">{label}</p>
          <p className="mt-2 text-3xl font-bold text-gray-950">{value}</p>
        </div>
        <div className="text-primary">{icon}</div>
      </div>
    </Card>
  );
}

function QuickAction({ href, icon, label }: { href: string; icon: ReactNode; label: string }) {
  return (
    <Link href={href} className="inline-flex min-h-10 items-center gap-2 rounded-md border border-gray-200 px-3 text-sm font-semibold text-gray-700 hover:bg-gray-50 active:bg-gray-100">
      {icon}
      {label}
    </Link>
  );
}
