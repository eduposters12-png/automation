import { ArrowRight, BarChart3, ImageIcon, UploadCloud } from "lucide-react";
import Link from "next/link";

import { Navbar } from "@/components/Navbar";
import { Card } from "@/components/ui/Card";

const features = [
  ["Shop Analysis", "Claude studies your Etsy shop and surfaces product opportunities.", BarChart3],
  ["Image Generation", "Create polished listing images from approved product ideas.", ImageIcon],
  ["Auto-Listing", "Queue completed packages for Etsy upload from FastAPI.", UploadCloud]
] as const;

const faqs = [
  ["Do I need an Etsy API key?", "No. Sellers connect Etsy with OAuth."],
  ["Where do AI calls run?", "All AI calls run in FastAPI."],
  ["Can I review before upload?", "Yes. Manual review and ZIP download are included."],
  ["Can I cancel anytime?", "Yes. Subscription controls live in settings."],
  ["Is Sentry on the backend?", "No. Sentry is only configured for frontend UI tracking."],
  ["Does ListifyAI store Claude keys?", "Keys are encrypted before storage."]
];

export default function MarketingPage() {
  return (
    <main className="min-h-screen bg-white">
      <Navbar />
      <section className="bg-gray-950 text-white">
        <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
          <h1 className="max-w-4xl text-5xl font-bold tracking-tight">Automate Your Etsy Shop with AI</h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-gray-300">
            Claude analyzes your shop, AI generates your products, and we auto-list them on Etsy.
          </p>
          <Link href="/register" className="mt-8 inline-flex min-h-11 items-center gap-2 rounded-md bg-primary px-5 text-sm font-semibold text-white hover:bg-indigo-500 active:bg-indigo-600">
            Start Free Trial
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="grid gap-5 md:grid-cols-3">
          {features.map(([title, text, Icon]) => (
            <Card key={title}>
              <Icon className="h-6 w-6 text-primary" />
              <h2 className="mt-4 text-lg font-bold text-gray-950">{title}</h2>
              <p className="mt-2 text-sm leading-6 text-gray-600">{text}</p>
            </Card>
          ))}
        </div>
      </section>

      <section className="border-y border-gray-100 bg-gray-50">
        <div className="mx-auto grid max-w-7xl gap-5 px-4 py-16 sm:px-6 md:grid-cols-3 lg:px-8">
          {[
            ["Basic", "$19/mo"],
            ["Pro", "$49/mo"],
            ["Agency", "$99/mo"]
          ].map(([name, price]) => (
            <Card key={name}>
              <h2 className="text-lg font-bold text-gray-950">{name}</h2>
              <p className="mt-3 text-3xl font-bold text-gray-950">{price}</p>
              <Link href="/register" className="mt-5 inline-flex min-h-10 items-center rounded-md bg-primary px-4 text-sm font-semibold text-white hover:bg-indigo-500 active:bg-indigo-600">
                Start
              </Link>
            </Card>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-4 py-16 sm:px-6 lg:px-8">
        <h2 className="text-2xl font-bold text-gray-950">FAQ</h2>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {faqs.map(([question, answer]) => (
            <div key={question} className="rounded-lg border border-gray-200 p-4">
              <h3 className="font-semibold text-gray-950">{question}</h3>
              <p className="mt-2 text-sm text-gray-600">{answer}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t border-gray-100 px-4 py-8 text-center text-sm text-gray-500">
        <div className="flex justify-center gap-4">
          <Link href="/login">Login</Link>
          <Link href="/register">Register</Link>
          <Link href="/upgrade">Pricing</Link>
        </div>
        <p className="mt-4">Copyright 2026 ListifyAI</p>
      </footer>
    </main>
  );
}
