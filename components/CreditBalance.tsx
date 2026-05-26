"use client";

import { AlertTriangle, Coins, Zap } from "lucide-react";
import { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { CreditBalance as CreditBalanceResponse } from "@/lib/types";

export function CreditBalance() {
  const [balance, setBalance] = useState<number | null>(null);

  useEffect(() => {
    async function loadBalance() {
      try {
        const response = await apiFetch<CreditBalanceResponse>("/credits/balance");
        setBalance(response.credit_balance);
      } catch {
        setBalance(null);
      }
    }

    void loadBalance();
  }, []);

  if (balance === null) {
    return null;
  }

  const isEmpty = balance === 0;
  const isLow = balance > 0 && balance < 20;
  const Icon = isEmpty || isLow ? AlertTriangle : balance >= 100 ? Coins : Zap;

  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-md border px-3 py-2 text-sm font-semibold",
        isEmpty
          ? "border-red-400/40 bg-red-500/10 text-red-200"
          : isLow
            ? "border-amber-300/40 bg-amber-400/10 text-amber-100"
            : "border-white/10 bg-white/5 text-gray-100"
      )}
    >
      <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
      <span>{balance} credits</span>
    </div>
  );
}
