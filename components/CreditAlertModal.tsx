"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { cn } from "@/lib/utils";
import type { CreditAlertState, CreditStatus } from "@/lib/types";

type CreditAlertModalProps = {
  alertState: CreditAlertState;
  creditStatus: CreditStatus | null;
  onDismiss: () => void;
  onUpgrade: () => void;
};

function clampPercent(value: number) {
  return Math.max(0, Math.min(100, value));
}

function daysText(days: number | null | undefined) {
  if (days === null || days === undefined) {
    return "soon";
  }
  return `${days} ${days === 1 ? "day" : "days"}`;
}

function formatResetDate(value: string | null | undefined) {
  if (!value) {
    return "Next reset date unavailable";
  }
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric"
  }).format(new Date(value));
}

function ProgressBar({ percent }: { percent: number }) {
  return (
    <div className="h-2 overflow-hidden rounded-full bg-amber-100">
      <div className="h-full rounded-full bg-amber-500" style={{ width: `${clampPercent(percent)}%` }} />
    </div>
  );
}

function OptionCard({
  title,
  body,
  children
}: {
  title: string;
  body: string;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col rounded-lg border border-gray-200 p-4">
      <h3 className="text-sm font-semibold text-gray-950">{title}</h3>
      <p className="mt-2 flex-1 text-sm text-gray-600">{body}</p>
      <div className="mt-4">{children}</div>
    </div>
  );
}

export function CreditAlertModal({
  alertState,
  creditStatus,
  onDismiss,
  onUpgrade
}: CreditAlertModalProps) {
  if (!alertState.show || !alertState.type || !creditStatus) {
    return null;
  }

  const software = creditStatus.software_credits;
  const resetDays = daysText(software.days_until_reset);
  const maxWidthClassName = alertState.type === "both_depleted" ? "max-w-lg" : "max-w-md";

  if (alertState.type === "software_low") {
    return (
      <Modal open title="⚠️ Credits Running Low" onClose={onDismiss} maxWidthClassName={maxWidthClassName}>
        <div className="animate-fade-in space-y-4">
          <p className="text-sm leading-6 text-gray-600">
            You have {software.balance} of {software.plan_total} credits remaining this month.
          </p>
          <ProgressBar percent={software.percent_remaining} />
          <p className="text-sm font-medium text-gray-700">Credits reset in {resetDays}.</p>
          <p className="text-sm font-medium text-gray-700">Claude API: ✅ Working fine</p>
          <div className="flex flex-col gap-2 sm:flex-row sm:justify-end">
            <Button type="button" onClick={onUpgrade}>
              Upgrade Plan
            </Button>
            <Button type="button" variant="ghost" onClick={onDismiss}>
              Got it
            </Button>
          </div>
        </div>
      </Modal>
    );
  }

  if (alertState.type === "software_depleted") {
    return (
      <Modal open title="🔴 Software Credits Exhausted" onClose={onDismiss} maxWidthClassName={maxWidthClassName}>
        <div className="animate-fade-in space-y-5">
          <div className="space-y-2 text-sm leading-6 text-gray-600">
            <p>Your {creditStatus.plan} plan credits for this month are used up.</p>
            <p className="font-semibold text-gray-800">
              {software.balance} / {software.plan_total} credits remaining
            </p>
            <p>Your Claude API key is still working - you won&apos;t lose anything.</p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <OptionCard title="Upgrade Your Plan" body="Get more credits immediately">
              <Button type="button" className="w-full" onClick={onUpgrade}>
                Upgrade Now →
              </Button>
            </OptionCard>
            <OptionCard title="Wait for Reset" body={`Credits reset in ${resetDays}`}>
              <p className="mb-3 text-xs font-semibold text-gray-500">{formatResetDate(software.reset_at)}</p>
              <Button type="button" variant="ghost" className="w-full" onClick={onDismiss}>
                Remind Me Later
              </Button>
            </OptionCard>
          </div>
        </div>
      </Modal>
    );
  }

  if (alertState.type === "claude_depleted") {
    return (
      <Modal open title="🟡 Claude API Credits Exhausted" onClose={onDismiss} maxWidthClassName={maxWidthClassName}>
        <div className="animate-fade-in space-y-5">
          <div className="space-y-2 text-sm leading-6 text-gray-600">
            <p>Your personal Claude API account has run out of credits.</p>
            <p>(This is separate from your ListifyAI subscription)</p>
          </div>
          <div className="rounded-lg bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-900">
            <p>Your ListifyAI software credits are safe: {software.balance} credits remaining</p>
            <p>These will NOT expire because of this.</p>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-950">What is affected</h3>
            <ul className="mt-3 space-y-2 text-sm text-gray-700">
              <li>❌ Listing copy writing</li>
              <li>❌ Shop analysis</li>
              <li>✅ Image generation (still works)</li>
              <li>✅ Video generation (still works)</li>
              <li>✅ Etsy upload (still works)</li>
            </ul>
          </div>
          <div className="space-y-3">
            <p className="text-sm text-gray-600">Top up your Claude API credits at Anthropic&apos;s console.</p>
            <div className="flex flex-col gap-2 sm:flex-row sm:justify-end">
              <Button
                type="button"
                onClick={() => window.open("https://console.anthropic.com/settings/billing", "_blank", "noopener,noreferrer")}
              >
                Go to console.anthropic.com →
              </Button>
              <Button type="button" variant="ghost" onClick={onDismiss}>
                I&apos;ll do it later
              </Button>
            </div>
          </div>
          <p className="text-xs text-gray-500">
            Or update your Claude API key in{" "}
            <Link href="/settings" className="font-semibold text-primary">
              Settings
            </Link>{" "}
            if you have a different key.
          </p>
        </div>
      </Modal>
    );
  }

  return (
    <Modal open title="🔴 Action Required - Two Things Need Attention" onClose={onDismiss} maxWidthClassName={maxWidthClassName}>
      <div className="animate-fade-in space-y-5">
        <div className="grid gap-4">
          {[
            {
              step: "1",
              title: "Top Up Claude API",
              body: "Your Anthropic account has run out of credits.",
              action: (
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => window.open("https://console.anthropic.com/settings/billing", "_blank", "noopener,noreferrer")}
                >
                  console.anthropic.com →
                </Button>
              )
            },
            {
              step: "2",
              title: "Upgrade Your ListifyAI Plan",
              body: "Your software credits are also exhausted.",
              action: (
                <Button type="button" onClick={onUpgrade}>
                  Upgrade Plan
                </Button>
              )
            }
          ].map((item) => (
            <div key={item.step} className="flex gap-3 rounded-lg border border-gray-200 p-4">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gray-950 text-sm font-bold text-white">
                {item.step}
              </div>
              <div className="min-w-0 flex-1">
                <h3 className="text-sm font-semibold text-gray-950">{item.title}</h3>
                <p className="mt-1 text-sm text-gray-600">{item.body}</p>
                <div className="mt-3">{item.action}</div>
              </div>
            </div>
          ))}
        </div>
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-800">
          Do both steps to resume full functionality. Doing only one will still leave some features unavailable.
        </div>
        <Link
          href="mailto:support@listifyai.com"
          className={cn("block text-center text-sm font-semibold text-primary")}
        >
          Questions? Contact support
        </Link>
      </div>
    </Modal>
  );
}
