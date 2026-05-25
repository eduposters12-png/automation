import { ArrowRight, BarChart3, Film, ImageIcon, Store } from "lucide-react";
import Link from "next/link";

import { Navbar } from "@/components/Navbar";

const featureCards = [
  ["Shop analysis", "Trend-backed niches", BarChart3],
  ["Product images", "GPT-4o asset jobs", ImageIcon],
  ["Listing videos", "Gemini video jobs", Film],
  ["Etsy uploads", "OAuth token upload queue", Store]
] as const;

export default function HomePage() {
  return (
    <main className="min-h-screen bg-white">
      <Navbar />
      <section className="border-b border-gray-100">
        <div className="mx-auto grid max-w-7xl gap-10 px-4 py-14 sm:px-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(480px,1.1fr)] lg:px-8 lg:py-20">
          <div className="flex flex-col justify-center">
            <p className="mb-3 text-sm font-semibold uppercase tracking-wide text-primary">ListifyAI</p>
            <h1 className="max-w-3xl text-4xl font-bold tracking-tight text-gray-950 sm:text-5xl">
              AI listing operations for Etsy sellers
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-gray-600">
              Connect Etsy, add Claude, and turn shop analysis into queued listing workflows for images, videos, and uploads.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link
                href="/register"
                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-md bg-primary px-5 text-sm font-semibold text-white transition hover:bg-indigo-500"
              >
                Start free
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
              <Link
                href="/login"
                className="inline-flex min-h-11 items-center justify-center rounded-md border border-gray-200 px-5 text-sm font-semibold text-gray-900 transition hover:bg-gray-50"
              >
                Login
              </Link>
            </div>
          </div>

          <div className="rounded-lg border border-gray-200 bg-gray-950 p-4 shadow-soft">
            <div className="rounded-md bg-white">
              <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
                <div>
                  <div className="text-sm font-semibold text-gray-950">Shop Command Center</div>
                  <div className="text-xs text-gray-500">Connected Etsy OAuth workspace</div>
                </div>
                <div className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">Live</div>
              </div>
              <div className="grid gap-4 p-5 sm:grid-cols-2">
                {featureCards.map(([title, text, Icon]) => (
                  <div key={title} className="rounded-lg border border-gray-100 p-4">
                    <Icon className="mb-4 h-5 w-5 text-primary" aria-hidden="true" />
                    <div className="text-sm font-semibold text-gray-950">{title}</div>
                    <div className="mt-1 text-xs text-gray-500">{text}</div>
                  </div>
                ))}
              </div>
              <div className="border-t border-gray-100 p-5">
                <div className="h-2 rounded-full bg-gray-100">
                  <div className="h-2 w-2/3 rounded-full bg-primary" />
                </div>
                <div className="mt-3 grid grid-cols-3 gap-3 text-center text-xs">
                  <div className="rounded-md bg-gray-50 p-3 font-semibold text-gray-700">Analyze</div>
                  <div className="rounded-md bg-gray-50 p-3 font-semibold text-gray-700">Generate</div>
                  <div className="rounded-md bg-gray-50 p-3 font-semibold text-gray-700">Upload</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
