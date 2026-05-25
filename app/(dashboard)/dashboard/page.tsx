import { AlertCircle, CheckCircle2, ListChecks, Store, Zap } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { getDashboardStats } from "@/lib/server-api";
import { formatLimit } from "@/lib/plans";

export default async function DashboardPage() {
  const stats = await getDashboardStats();

  if (!stats) {
    return null;
  }

  const setupComplete = stats.etsy_connected && stats.claude_key_added;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-950">Dashboard</h1>
          <p className="mt-1 text-sm text-gray-600">
            {stats.shop_name || "Your Etsy shop"} workspace
          </p>
        </div>
        <Badge tone="indigo">{stats.plan}</Badge>
      </div>

      {!setupComplete ? (
        <div className="flex flex-col gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" aria-hidden="true" />
            <div>
              <p className="font-semibold text-amber-900">Complete onboarding</p>
              <p className="text-sm text-amber-800">Etsy OAuth and Claude are required before listing jobs can run.</p>
            </div>
          </div>
          <Link
            href="/onboarding"
            className="inline-flex min-h-10 items-center justify-center rounded-md bg-amber-900 px-4 text-sm font-semibold text-white transition hover:bg-amber-800"
          >
            Open onboarding
          </Link>
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Total listings</p>
              <p className="mt-2 text-3xl font-bold text-gray-950">{stats.total_listings}</p>
            </div>
            <ListChecks className="h-8 w-8 text-primary" aria-hidden="true" />
          </div>
        </Card>
        <Card>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">This month</p>
              <p className="mt-2 text-3xl font-bold text-gray-950">
                {stats.monthly_usage}/{formatLimit(stats.monthly_limit)}
              </p>
            </div>
            <Zap className="h-8 w-8 text-primary" aria-hidden="true" />
          </div>
        </Card>
        <Card>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Shop slots</p>
              <p className="mt-2 text-3xl font-bold text-gray-950">{stats.shop_limit}</p>
            </div>
            <Store className="h-8 w-8 text-primary" aria-hidden="true" />
          </div>
        </Card>
      </div>

      <Card>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="flex items-center gap-3">
            {stats.etsy_connected ? (
              <CheckCircle2 className="h-5 w-5 text-emerald-600" aria-hidden="true" />
            ) : (
              <AlertCircle className="h-5 w-5 text-amber-600" aria-hidden="true" />
            )}
            <div>
              <p className="font-semibold text-gray-950">Etsy OAuth</p>
              <p className="text-sm text-gray-500">{stats.etsy_connected ? "Connected" : "Not connected"}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {stats.claude_key_added ? (
              <CheckCircle2 className="h-5 w-5 text-emerald-600" aria-hidden="true" />
            ) : (
              <AlertCircle className="h-5 w-5 text-amber-600" aria-hidden="true" />
            )}
            <div>
              <p className="font-semibold text-gray-950">Claude API</p>
              <p className="text-sm text-gray-500">{stats.claude_key_added ? "Saved encrypted" : "Missing"}</p>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
