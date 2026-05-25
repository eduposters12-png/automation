import { CheckCircle2 } from "lucide-react";

import { UpgradeButton } from "@/components/UpgradeButton";
import { Card } from "@/components/ui/Card";
import { planDetails } from "@/lib/plans";

export default function UpgradePage() {
  const plans = Object.values(planDetails);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-950">Upgrade</h1>
        <p className="mt-1 text-sm text-gray-600">Choose the listing volume that matches your Etsy workflow.</p>
      </div>
      <div className="grid gap-5 lg:grid-cols-3">
        {plans.map((plan) => (
          <Card key={plan.name} className="flex flex-col">
            <div>
              <h2 className="text-lg font-bold text-gray-950">{plan.name}</h2>
              <div className="mt-4 flex items-end gap-1">
                <span className="text-4xl font-bold text-gray-950">{plan.price}</span>
                <span className="pb-1 text-sm font-medium text-gray-500">/month</span>
              </div>
            </div>
            <div className="mt-6 space-y-3 text-sm text-gray-700">
              {[plan.listings, plan.shops, "Stripe subscription billing"].map((item) => (
                <div key={item} className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" aria-hidden="true" />
                  <span>{item}</span>
                </div>
              ))}
            </div>
            <div className="mt-6">
              <UpgradeButton plan={plan.planId} />
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
