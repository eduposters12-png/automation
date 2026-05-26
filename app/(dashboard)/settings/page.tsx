"use client";

import * as Sentry from "@sentry/nextjs";
import { CheckCircle2, Coins, ExternalLink, KeyRound, Loader2, Store, Trash2, XCircle } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import toast from "react-hot-toast";

import { UsageBar } from "@/components/UsageBar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { apiFetch } from "@/lib/api";
import type {
  AnalyticsUsageResponse,
  AuthResponse,
  CreditBalance,
  CreditHistoryEntry,
  EtsyConnectionStatus,
  SettingsResponse,
  TestConnectionResponse
} from "@/lib/types";

const featureText = {
  FREE: ["20 signup credits", "Explore onboarding"],
  BASIC: ["150 credits/month", "20 images/month", "20 uploads/month"],
  PRO: ["600 credits/month", "100 images/month", "50 videos/month", "100 uploads/month"],
  AGENCY: ["2000 credits/month", "500 images/month", "200 videos/month", "500 uploads/month"]
};

const disconnectedEtsyStatus: EtsyConnectionStatus = {
  connected: false,
  shop_name: null,
  shop_url: null,
  etsy_shop_id: null,
  connected_at: null
};

function captureUiError(error: unknown) {
  Sentry.captureException(error);
}

function formatConnectedDate(value: string | null) {
  if (!value) {
    return "Not available";
  }

  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric"
  }).format(new Date(value));
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [usage, setUsage] = useState<AnalyticsUsageResponse | null>(null);
  const [credits, setCredits] = useState<CreditBalance | null>(null);
  const [creditHistory, setCreditHistory] = useState<CreditHistoryEntry[]>([]);
  const [etsyStatus, setEtsyStatus] = useState<EtsyConnectionStatus | null>(null);
  const [claudeKey, setClaudeKey] = useState("");
  const [name, setName] = useState("");
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [deleteText, setDeleteText] = useState("");
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [etsyLoading, setEtsyLoading] = useState(true);
  const [etsyConnecting, setEtsyConnecting] = useState(false);
  const [etsyDisconnecting, setEtsyDisconnecting] = useState(false);
  const [showDisconnectConfirm, setShowDisconnectConfirm] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<Record<string, boolean | null>>({ etsy: null, claude: null });

  async function loadSettings() {
    setLoading(true);
    try {
      const [settingsResponse, usageResponse] = await Promise.all([
        apiFetch<SettingsResponse>("/settings"),
        apiFetch<AnalyticsUsageResponse>("/analytics/usage")
      ]);
      setSettings(settingsResponse);
      setUsage(usageResponse);
      setName(settingsResponse.name);
      const [creditResponse, historyResponse] = await Promise.all([
        apiFetch<CreditBalance>("/credits/balance"),
        apiFetch<CreditHistoryEntry[]>("/credits/history?limit=10")
      ]);
      setCredits(creditResponse);
      setCreditHistory(historyResponse);
    } catch (error) {
      captureUiError(error);
      toast.error("Could not load settings");
    } finally {
      setLoading(false);
    }
  }

  async function loadEtsyStatus() {
    setEtsyLoading(true);
    try {
      const response = await apiFetch<EtsyConnectionStatus>("/etsy/connection-status");
      setEtsyStatus(response);
    } catch (error) {
      captureUiError(error);
      setEtsyStatus(disconnectedEtsyStatus);
    } finally {
      setEtsyLoading(false);
    }
  }

  useEffect(() => {
    void loadSettings();
    void loadEtsyStatus();
  }, []);

  async function connectEtsy() {
    setEtsyConnecting(true);
    try {
      const data = await apiFetch<{ auth_url: string }>("/etsy/connect");
      window.location.assign(data.auth_url);
    } catch (error) {
      captureUiError(error);
      toast.error(error instanceof Error ? error.message : "Could not start Etsy OAuth");
      setEtsyConnecting(false);
    }
  }

  async function handleDisconnect() {
    setEtsyDisconnecting(true);
    try {
      const response = await apiFetch<{ success: boolean; message: string }>("/etsy/disconnect", { method: "POST" });
      setEtsyStatus(disconnectedEtsyStatus);
      setSettings((current) => current ? { ...current, shop_name: null, etsy_connected: false } : current);
      setConnectionStatus((current) => ({ ...current, etsy: false }));
      setShowDisconnectConfirm(false);
      toast.success(response.message);
    } catch (error) {
      captureUiError(error);
      toast.error(error instanceof Error ? error.message : "Could not disconnect Etsy");
    } finally {
      setEtsyDisconnecting(false);
    }
  }

  async function updateClaude() {
    if (!claudeKey.trim()) return;
    try {
      const response = await apiFetch<SettingsResponse>("/settings", {
        method: "PATCH",
        json: { claude_api_key: claudeKey.trim() }
      });
      setSettings(response);
      setClaudeKey("");
      toast.success("Claude key updated");
    } catch (error) {
      captureUiError(error);
      toast.error(error instanceof Error ? error.message : "Could not update Claude key");
    }
  }

  async function testConnection(keyType: "etsy" | "claude") {
    try {
      const response = await apiFetch<TestConnectionResponse>("/shop/test-connection", {
        method: "POST",
        json: { key_type: keyType }
      });
      setConnectionStatus((current) => ({ ...current, [keyType]: response.success }));
      toast.success(response.message);
    } catch (error) {
      captureUiError(error);
      setConnectionStatus((current) => ({ ...current, [keyType]: false }));
      toast.error(error instanceof Error ? error.message : "Connection test failed");
    }
  }

  async function checkout(plan: string) {
    try {
      const response = await apiFetch<{ url: string }>("/stripe/checkout", { method: "POST", json: { plan } });
      window.location.assign(response.url);
    } catch (error) {
      captureUiError(error);
      toast.error(error instanceof Error ? error.message : "Could not start checkout");
    }
  }

  async function cancelSubscription() {
    try {
      await apiFetch<{ success: boolean }>("/stripe/cancel", { method: "POST" });
      toast.success("Subscription cancelled");
      await loadSettings();
    } catch (error) {
      captureUiError(error);
      toast.error(error instanceof Error ? error.message : "Could not cancel subscription");
    }
  }

  async function loadFullCreditHistory() {
    try {
      const response = await apiFetch<CreditHistoryEntry[]>("/credits/history?limit=100");
      setCreditHistory(response);
    } catch (error) {
      captureUiError(error);
      toast.error("Could not load credit history");
    }
  }

  async function updateProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const response = await apiFetch<AuthResponse>("/auth/profile", { method: "PATCH", json: { name } });
      setName(response.user.name);
      toast.success("Profile updated");
    } catch (error) {
      captureUiError(error);
      toast.error(error instanceof Error ? error.message : "Could not update profile");
    }
  }

  async function changePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await apiFetch<{ success: boolean }>("/auth/change-password", {
        method: "POST",
        json: { old_password: oldPassword, new_password: newPassword }
      });
      setOldPassword("");
      setNewPassword("");
      toast.success("Password updated");
    } catch (error) {
      captureUiError(error);
      toast.error(error instanceof Error ? error.message : "Could not change password");
    }
  }

  async function deleteAccount() {
    if (deleteText !== "DELETE") return;
    try {
      await apiFetch<{ success: boolean }>("/auth/account", { method: "DELETE" });
      window.location.assign("/register");
    } catch (error) {
      captureUiError(error);
      toast.error(error instanceof Error ? error.message : "Could not delete account");
    }
  }

  if (loading || !settings || !usage) {
    return <Card className="flex min-h-80 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></Card>;
  }

  return (
    <div className="animate-fade-in space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-950">Settings</h1>
        <p className="mt-1 text-sm text-gray-600">Shop, subscription, and account controls.</p>
      </div>

      <Card className="space-y-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-indigo-50 text-primary">
              <Store className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-gray-950">Etsy Connection</h2>
              <p className="mt-1 text-sm text-gray-600">Manage the Etsy shop linked to this account.</p>
            </div>
          </div>
          {!etsyLoading && etsyStatus ? (
            <span className={etsyStatus.connected ? "inline-flex items-center gap-2 text-sm font-semibold text-emerald-700" : "inline-flex items-center gap-2 text-sm font-semibold text-red-700"}>
              <span className={etsyStatus.connected ? "h-2 w-2 rounded-full bg-emerald-500" : "h-2 w-2 rounded-full bg-red-500"} />
              {etsyStatus.connected ? "Connected" : "Not Connected"}
            </span>
          ) : null}
        </div>

        {etsyLoading ? (
          <div className="flex items-center gap-3 rounded-lg border border-gray-100 bg-gray-50 px-4 py-4 text-sm font-medium text-gray-600">
            <Loader2 className="h-4 w-4 animate-spin text-primary" aria-hidden="true" />
            Checking connection...
          </div>
        ) : etsyStatus?.connected ? (
          <div className="space-y-4">
            <div className="rounded-lg bg-gray-50 p-4">
              <p className="text-lg font-bold text-gray-950">{etsyStatus.shop_name || "Connected Etsy shop"}</p>
              {etsyStatus.shop_url ? (
                <a
                  href={etsyStatus.shop_url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-1 inline-flex items-center gap-1 text-sm font-medium text-primary hover:text-indigo-500"
                >
                  {etsyStatus.shop_url}
                  <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                </a>
              ) : null}
              <div className="mt-3 space-y-1 text-sm text-gray-600">
                <p>Connected since: {formatConnectedDate(etsyStatus.connected_at)}</p>
                <p>Etsy Shop ID: {etsyStatus.etsy_shop_id || "Not available"}</p>
              </div>
            </div>
            <Button
              type="button"
              variant="secondary"
              className="border-red-300 text-red-600 hover:bg-red-50"
              onClick={() => setShowDisconnectConfirm(true)}
            >
              Disconnect
            </Button>
            {showDisconnectConfirm ? (
              <div className="space-y-4 rounded-lg border border-red-200 bg-red-50 p-4">
                <div>
                  <p className="text-sm font-semibold text-red-800">Are you sure you want to disconnect your Etsy shop?</p>
                  <p className="mt-1 text-sm leading-6 text-red-700">
                    This will remove your Etsy connection. Your listings and settings will not be deleted. You can reconnect anytime.
                  </p>
                </div>
                <div className="flex flex-col gap-2 sm:flex-row">
                  <Button
                    type="button"
                    variant="danger"
                    loading={etsyDisconnecting}
                    onClick={handleDisconnect}
                  >
                    Yes, Disconnect
                  </Button>
                  <Button type="button" variant="ghost" onClick={() => setShowDisconnectConfirm(false)}>
                    Cancel
                  </Button>
                </div>
              </div>
            ) : null}
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm leading-6 text-gray-600">Connect your Etsy shop to enable automatic listing uploads.</p>
            <Button type="button" onClick={connectEtsy} loading={etsyConnecting}>
              Connect Etsy Shop
            </Button>
          </div>
        )}
      </Card>

      <Card className="space-y-5">
        <h2 className="text-base font-semibold text-gray-950">Shop Settings</h2>
        <Input label="Shop name" name="shop_name" value={settings.shop_name || "Not connected"} readOnly />
        <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto_auto]">
          <Input
            label="Claude API Key"
            name="claude_api_key"
            type="password"
            value={claudeKey}
            placeholder={settings.claude_key_last4 ? `Saved key ending in ${settings.claude_key_last4}` : settings.claude_key_added ? "Saved key is hidden" : "sk-ant-..."}
            onChange={(event) => setClaudeKey(event.target.value)}
          />
          <Button type="button" className="self-end" onClick={updateClaude} icon={<KeyRound className="h-4 w-4" />}>Update</Button>
          <Button type="button" variant="secondary" className="self-end" onClick={() => testConnection("claude")} icon={connectionStatus.claude === false ? <XCircle className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}>Test Claude</Button>
        </div>
        <Button type="button" variant="secondary" onClick={() => testConnection("etsy")} icon={connectionStatus.etsy === false ? <XCircle className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}>Test Etsy</Button>
      </Card>

      <Card className="space-y-5">
        <h2 className="text-base font-semibold text-gray-950">Subscription</h2>
        <div>
          <p className="text-2xl font-bold text-gray-950">{settings.plan}</p>
          <div className="mt-2 flex flex-wrap gap-2 text-sm text-gray-600">
            {featureText[settings.plan as keyof typeof featureText].map((item) => <span key={item}>{item}</span>)}
          </div>
        </div>
        <UsageBar label="Images" used={usage.usage_with_limits.IMAGE_GENERATED.used} limit={usage.usage_with_limits.IMAGE_GENERATED.limit} />
        <UsageBar label="Videos" used={usage.usage_with_limits.VIDEO_GENERATED.used} limit={usage.usage_with_limits.VIDEO_GENERATED.limit} />
        <UsageBar label="Uploads" used={usage.usage_with_limits.LISTING_UPLOADED.used} limit={usage.usage_with_limits.LISTING_UPLOADED.limit} />
        <div className="flex flex-wrap gap-2">
          <Button type="button" onClick={() => checkout("PRO")}>Change Plan</Button>
          <Button type="button" variant="danger" onClick={cancelSubscription}>Cancel Subscription</Button>
        </div>
      </Card>

      <Card className="space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-base font-semibold text-gray-950">Credits & Usage</h2>
          <div className="inline-flex items-center gap-2 rounded-md bg-indigo-50 px-3 py-2 text-sm font-semibold text-indigo-700">
            <Coins className="h-4 w-4" />
            {credits?.credit_balance ?? 0} credits
          </div>
        </div>
        <div className="divide-y divide-gray-100 rounded-lg border border-gray-100">
          {creditHistory.length ? creditHistory.map((entry) => (
            <div key={`${entry.created_at}-${entry.action}-${entry.balance_after}`} className="grid gap-2 px-4 py-3 text-sm sm:grid-cols-[minmax(0,1fr)_auto_auto] sm:items-center">
              <span className="font-medium text-gray-800">{formatCreditAction(entry.action)}</span>
              <span className={entry.credits_delta < 0 ? "font-semibold text-red-600" : "font-semibold text-emerald-700"}>
                {entry.credits_delta > 0 ? `+${entry.credits_delta}` : entry.credits_delta}
              </span>
              <span className="text-gray-500">{new Date(entry.created_at).toLocaleDateString()}</span>
            </div>
          )) : (
            <div className="px-4 py-6 text-sm text-gray-500">No credit transactions yet.</div>
          )}
        </div>
        <Button type="button" variant="secondary" onClick={loadFullCreditHistory}>
          View full history
        </Button>
      </Card>

      <Card className="space-y-5">
        <h2 className="text-base font-semibold text-gray-950">Account</h2>
        <form className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto]" onSubmit={updateProfile}>
          <Input label="Display name" name="name" value={name} onChange={(event) => setName(event.target.value)} />
          <Button type="submit" className="self-end">Save</Button>
        </form>
        <Input label="Email" name="email" value={settings.email} readOnly />
        <form className="grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]" onSubmit={changePassword}>
          <Input label="Current password" name="old_password" type="password" value={oldPassword} onChange={(event) => setOldPassword(event.target.value)} />
          <Input label="New password" name="new_password" type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} />
          <Button type="submit" className="self-end">Change Password</Button>
        </form>
        <Button type="button" variant="danger" onClick={() => setDeleteOpen(true)} icon={<Trash2 className="h-4 w-4" />}>Delete Account</Button>
      </Card>

      <Modal open={deleteOpen} title="Delete account" onClose={() => setDeleteOpen(false)}>
        <div className="space-y-4">
          <Input label="Type DELETE to confirm" name="delete_confirm" value={deleteText} onChange={(event) => setDeleteText(event.target.value)} />
          <Button type="button" variant="danger" disabled={deleteText !== "DELETE"} onClick={deleteAccount} className="w-full">Delete Account</Button>
        </div>
      </Modal>
    </div>
  );
}

function formatCreditAction(action: string) {
  return action
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
