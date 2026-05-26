"use client";

import Link from "next/link";

import { cn } from "@/lib/utils";

type UsageBarProps = {
  label: string;
  used: number;
  limit: number;
};

export function UsageBar({ label, used, limit }: UsageBarProps) {
  const percent = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 100;
  const danger = percent >= 95;
  const warning = percent >= 80;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="font-semibold text-gray-800">{label}: {used}/{limit} used this month</span>
        {warning ? <Link href="/upgrade" className="font-semibold text-primary hover:text-indigo-500">Upgrade</Link> : null}
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-gray-100">
        <div
          className={cn(
            "h-full rounded-full transition-all",
            danger ? "bg-red-500" : warning ? "bg-amber-500" : "bg-primary"
          )}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
