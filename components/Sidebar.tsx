"use client";

import {
  BarChart3,
  CreditCard,
  FileText,
  Home,
  ListChecks,
  LogOut,
  PlusCircle,
  Settings,
  Sparkles
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import toast from "react-hot-toast";

import { CreditAlertModal } from "@/components/CreditAlertModal";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useCreditStatus } from "@/lib/useCreditStatus";
import type { User } from "@/lib/types";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: Home },
  { href: "/shop-analysis", label: "Shop Analysis", icon: BarChart3 },
  { href: "/new-listing", label: "New Listing", icon: PlusCircle },
  { href: "/new-listing/multi-page", label: "Multi-Page Product", icon: FileText },
  { href: "/my-listings", label: "My Listings", icon: ListChecks },
  { href: "/settings", label: "Settings", icon: Settings },
  { href: "/upgrade", label: "Upgrade", icon: CreditCard }
];

export function Sidebar({ user }: { user: User }) {
  const pathname = usePathname();
  const router = useRouter();
  const { creditStatus, loading, dismissAlert } = useCreditStatus(true);
  const [showCreditModal, setShowCreditModal] = useState(false);

  async function logout() {
    try {
      await apiFetch("/auth/logout", { method: "POST" });
      toast.success("Logged out");
      router.push("/login");
      router.refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not log out");
    }
  }

  function handleUpgrade() {
    router.push("/upgrade");
    dismissAlert();
    setShowCreditModal(false);
  }

  const renderCreditStatus = () => {
    if (!creditStatus || loading) {
      return null;
    }

    const software = creditStatus.software_credits;
    if (creditStatus.alert_state === "ok" && software.percent_remaining > 60) {
      return <p className="px-1 text-xs font-medium text-gray-400">{software.balance} credits</p>;
    }

    if (creditStatus.alert_state === "software_low") {
      return (
        <div className="rounded-full border border-amber-300/40 bg-amber-400/10 px-3 py-2 text-xs font-semibold text-amber-100">
          ⚠️ {software.balance} credits left
        </div>
      );
    }

    if (creditStatus.alert_state === "software_depleted") {
      return (
        <div className="flex items-center justify-between gap-3 rounded-full border border-red-400/40 bg-red-500/10 px-3 py-2 text-xs font-semibold text-red-100">
          <span>🔴 No credits</span>
          <button type="button" className="text-white underline-offset-2 hover:underline" onClick={() => router.push("/upgrade")}>
            Upgrade
          </button>
        </div>
      );
    }

    if (creditStatus.alert_state === "claude_depleted") {
      return (
        <div className="rounded-full border border-yellow-300/40 bg-yellow-400/10 px-3 py-2 text-xs font-semibold text-yellow-100">
          🟡 Claude depleted
        </div>
      );
    }

    if (creditStatus.alert_state === "both_depleted") {
      return (
        <div className="flex items-center justify-between gap-3 rounded-full border border-red-400/40 bg-red-500/10 px-3 py-2 text-xs font-semibold text-red-100">
          <span>🔴 Action needed</span>
          <button type="button" className="text-white underline-offset-2 hover:underline" onClick={() => setShowCreditModal(true)}>
            Fix now
          </button>
        </div>
      );
    }

    return null;
  };

  const renderNavigation = () => (
    <nav className="flex gap-1 lg:flex-col">
      {navItems.map((item) => {
        const Icon = item.icon;
        const active = pathname === item.href;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex min-h-10 items-center gap-3 rounded-md px-3 text-sm font-medium transition",
              active
                ? "bg-white text-gray-950 lg:bg-white"
                : "text-gray-300 hover:bg-white/10 hover:text-white"
            )}
          >
            <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span className="hidden sm:inline">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );

  const creditStatusDisplay = renderCreditStatus();

  return (
    <>
      <aside className="hidden min-h-screen w-72 shrink-0 flex-col bg-sidebar px-4 py-5 text-white lg:flex">
        <div className="mb-8 flex items-center gap-3 px-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary">
            <Sparkles className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <div className="text-base font-bold">ListifyAI</div>
            <div className="text-xs text-gray-400">Etsy growth studio</div>
          </div>
        </div>
        {renderNavigation()}
        <div className="mt-auto space-y-3">
          <div className="rounded-lg border border-white/10 bg-white/5 p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold">{user.name}</p>
                <p className="truncate text-xs text-gray-400">{user.email}</p>
              </div>
              <Badge tone="indigo">{user.plan}</Badge>
            </div>
            {creditStatusDisplay ? <div className="mb-3">{creditStatusDisplay}</div> : null}
            <Button
              type="button"
              variant="ghost"
              className="w-full justify-start text-gray-200 hover:bg-white/10 hover:text-white"
              icon={<LogOut className="h-4 w-4" aria-hidden="true" />}
              onClick={logout}
            >
              Logout
            </Button>
          </div>
        </div>
      </aside>

      <div className="sticky top-0 z-30 border-b border-gray-200 bg-sidebar px-3 py-3 text-white lg:hidden">
        <div className="mb-3 flex items-center justify-between">
          <Link href="/dashboard" className="text-base font-bold">ListifyAI</Link>
          <Badge tone="indigo">{user.plan}</Badge>
        </div>
        <div className="overflow-x-auto">{renderNavigation()}</div>
      </div>
      <CreditAlertModal
        alertState={{
          show: showCreditModal,
          type: creditStatus?.alert_state === "both_depleted" ? "both_depleted" : null
        }}
        creditStatus={creditStatus}
        onDismiss={() => setShowCreditModal(false)}
        onUpgrade={handleUpgrade}
      />
    </>
  );
}
