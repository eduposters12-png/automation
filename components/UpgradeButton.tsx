"use client";

import { useState } from "react";
import toast from "react-hot-toast";

import { Button } from "@/components/ui/Button";
import { apiFetch } from "@/lib/api";

export function UpgradeButton({ plan }: { plan: string }) {
  const [loading, setLoading] = useState(false);

  async function checkout() {
    setLoading(true);
    try {
      const data = await apiFetch<{ url: string }>("/stripe/checkout", {
        method: "POST",
        json: { plan }
      });
      window.location.assign(data.url);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not start checkout");
      setLoading(false);
    }
  }

  return (
    <Button type="button" onClick={checkout} loading={loading} className="w-full">
      Upgrade
    </Button>
  );
}
