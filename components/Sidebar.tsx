"use client";

import {
  BarChart3,
  CreditCard,
  Home,
  ListChecks,
  LogOut,
  PlusCircle,
  Settings,
  Sparkles
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import toast from "react-hot-toast";

import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { User } from "@/lib/types";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: Home },
  { href: "/shop-analysis", label: "Shop Analysis", icon: BarChart3 },
  { href: "/new-listing", label: "New Listing", icon: PlusCircle },
  { href: "/my-listings", label: "My Listings", icon: ListChecks },
  { href: "/settings", label: "Settings", icon: Settings },
  { href: "/upgrade", label: "Upgrade", icon: CreditCard }
];

export function Sidebar({ user }: { user: User }) {
  const pathname = usePathname();
  const router = useRouter();

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
        <div className="mt-auto rounded-lg border border-white/10 bg-white/5 p-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">{user.name}</p>
              <p className="truncate text-xs text-gray-400">{user.email}</p>
            </div>
            <Badge tone="indigo">{user.plan}</Badge>
          </div>
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
      </aside>

      <div className="sticky top-0 z-30 border-b border-gray-200 bg-sidebar px-3 py-3 text-white lg:hidden">
        <div className="mb-3 flex items-center justify-between">
          <Link href="/dashboard" className="text-base font-bold">ListifyAI</Link>
          <Badge tone="indigo">{user.plan}</Badge>
        </div>
        <div className="overflow-x-auto">{renderNavigation()}</div>
      </div>
    </>
  );
}
