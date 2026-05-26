"use client";

import { BarChart3, PlusCircle } from "lucide-react";
import Link from "next/link";

import { Card } from "@/components/ui/Card";

export function NoListingsState() {
  return (
    <Card className="text-center">
      <PlusCircle className="mx-auto h-10 w-10 text-gray-300" />
      <h2 className="mt-4 text-base font-semibold text-gray-950">No listings yet</h2>
      <Link href="/new-listing" className="mt-4 inline-flex min-h-10 items-center justify-center rounded-md bg-primary px-4 text-sm font-semibold text-white hover:bg-indigo-500 active:bg-indigo-600">
        Create your first listing
      </Link>
    </Card>
  );
}

export function NoAnalysisState() {
  return (
    <Card className="text-center">
      <BarChart3 className="mx-auto h-10 w-10 text-gray-300" />
      <h2 className="mt-4 text-base font-semibold text-gray-950">Analyze your shop to get started</h2>
      <Link href="/shop-analysis" className="mt-4 inline-flex min-h-10 items-center justify-center rounded-md bg-primary px-4 text-sm font-semibold text-white hover:bg-indigo-500 active:bg-indigo-600">
        Analyze My Shop
      </Link>
    </Card>
  );
}
