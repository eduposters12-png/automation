"use client";

import * as Sentry from "@sentry/nextjs";
import { CheckCircle2 } from "lucide-react";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { apiFetch } from "@/lib/api";
import type { AuthResponse, Plan } from "@/lib/types";

const plans = [
  { id: "BASIC" as const, name: "Basic", price: 19, features: ["20 images/month", "20 uploads/month", "Single shop"] },
  { id: "PRO" as const, name: "Pro", price: 49, features: ["100 images/month", "50 videos/month", "100 uploads/month"] },
  { id: "AGENCY" as const, name: "Agency", price: 99, features: ["500 images/month", "200 videos/month", "500 uploads/month"] }
];

export default function UpgradePage() {
  const [currentPlan, setCurrentPlan] = useState<Plan>("FREE");
  const [annual, setAnnual] = useState(false);
  const [loadingPlan, setLoadingPlan] = useState<string | null>(null);

  useEffect(() => {
    async function loadPlan() {
      try {
        const auth = await apiFetch<AuthResponse>("/auth/me");
        setCurrentPlan(auth.user.plan);
      } catch (error) {
        Sentry.captureException(error);
        setCurrentPlan("FREE");
      }
    }
    void loadPlan();
  }, []);

  async function checkout(plan: Plan) {
    setLoadingPlan(plan);
    try {
      const response = await apiFetch<{ url: string }>("/stripe/checkout", {
        method: "POST",
        json: { plan, annual }
      });
      window.location.assign(response.url);
    } catch (error) {
      Sentry.captureException(error);
      toast.error(error instanceof Error ? error.message : "Could not start checkout");
    } finally {
      setLoadingPlan(null);
    }
  }

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-950">Upgrade</h1>
          <p className="mt-1 text-sm text-gray-600">Choose the plan that matches your Etsy workflow.</p>
        </div>
        <label className="inline-flex items-center gap-3 text-sm font-semibold text-gray-700">
          Annual billing
          <input type="checkbox" className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary" checked={annual} onChange={(event) => setAnnual(event.target.checked)} />
        </label>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        {plans.map((plan) => {
          const price = annual ? Math.round(plan.price * 0.8) : plan.price;
          const current = currentPlan === plan.id;
          return (
            <Card key={plan.id} className={current ? "border-primary ring-2 ring-indigo-100" : ""}>
              <div className="flex items-start justify-between gap-3">
                <h2 className="text-lg font-bold text-gray-950">{plan.name}</h2>
                {current ? <Badge tone="green">Current Plan</Badge> : null}
              </div>
              <div className="mt-4 flex items-end gap-1">
                <span className="text-4xl font-bold text-gray-950">${price}</span>
                <span className="pb-1 text-sm font-medium text-gray-500">/mo</span>
              </div>
              {annual ? <p className="mt-1 text-sm font-semibold text-emerald-700">20% annual discount</p> : null}
              <div className="mt-6 space-y-3 text-sm text-gray-700">
                {plan.features.map((feature) => (
                  <div key={feature} className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                    <span>{feature}</span>
                  </div>
                ))}
              </div>
              <Button type="button" className="mt-6 w-full" disabled={current} loading={loadingPlan === plan.id} onClick={() => checkout(plan.id)}>
                {current ? "Current Plan" : "Upgrade"}
              </Button>
            </Card>
          );
        })}
      </div>

      <Card>
        <h2 className="text-base font-semibold text-gray-950">Feature Comparison</h2>
        <div className="mt-4 grid gap-3 text-sm text-gray-700 md:grid-cols-3">
          <p>Basic: starter generation and upload capacity.</p>
          <p>Pro: video generation and higher monthly limits.</p>
          <p>Agency: high-volume shop and upload workflows.</p>
        </div>
        <p className="mt-5 rounded-lg bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-700">30-day money-back guarantee</p>
      </Card>
    </div>
  );
}
