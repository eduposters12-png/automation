"use client";

import * as Sentry from "@sentry/nextjs";
import { CheckCircle2, KeyRound, Loader2, Trash2, XCircle } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import toast from "react-hot-toast";

import { UsageBar } from "@/components/UsageBar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { apiFetch } from "@/lib/api";
import type { AnalyticsUsageResponse, AuthResponse, SettingsResponse, TestConnectionResponse } from "@/lib/types";

const featureText = {
  FREE: ["Explore onboarding", "No generation credits"],
  BASIC: ["20 images/month", "20 uploads/month"],
  PRO: ["100 images/month", "50 videos/month", "100 uploads/month"],
  AGENCY: ["500 images/month", "200 videos/month", "500 uploads/month"]
};

function captureUiError(error: unknown) {
  Sentry.captureException(error);
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [usage, setUsage] = useState<AnalyticsUsageResponse | null>(null);
  const [claudeKey, setClaudeKey] = useState("");
  const [name, setName] = useState("");
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [deleteText, setDeleteText] = useState("");
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [loading, setLoading] = useState(true);
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
    } catch (error) {
      captureUiError(error);
      toast.error("Could not load settings");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadSettings();
  }, []);

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
