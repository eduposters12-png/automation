"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import toast from "react-hot-toast";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { apiFetch } from "@/lib/api";
import type { SettingsResponse } from "@/lib/types";

export function SettingsForm({ initialSettings }: { initialSettings: SettingsResponse }) {
  const [settings, setSettings] = useState(initialSettings);
  const [claudeKey, setClaudeKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [connecting, setConnecting] = useState(false);

  async function connectEtsy() {
    setConnecting(true);
    try {
      const data = await apiFetch<{ auth_url: string }>("/etsy/connect");
      window.location.assign(data.auth_url);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not start Etsy OAuth");
      setConnecting(false);
    }
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const claudeKey = String(formData.get("claude_api_key") || "");
    setSaving(true);
    try {
      const nextSettings = await apiFetch<SettingsResponse>("/settings", {
        method: "PATCH",
        json: {
          name: formData.get("name"),
          shop_url: formData.get("shop_url"),
          niche: formData.get("niche"),
          claude_api_key: claudeKey.trim() ? claudeKey : undefined
        }
      });
      setSettings(nextSettings);
      setClaudeKey("");
      toast.success("Settings updated");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not update settings");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
      <Card>
        <form className="space-y-5" onSubmit={onSubmit}>
          <div className="grid gap-4 md:grid-cols-2">
            <Input label="Name" name="name" defaultValue={settings.name} required />
            <Input label="Email" name="email" defaultValue={settings.email} disabled />
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <Input label="Shop URL" name="shop_url" defaultValue={settings.shop_url || ""} />
            <Input label="Niche" name="niche" defaultValue={settings.niche || ""} placeholder="Digital planners, wall art, templates" />
          </div>
          <Input
            label="Claude API key"
            name="claude_api_key"
            type="password"
            autoComplete="off"
            value={claudeKey}
            onChange={(event) => setClaudeKey(event.target.value)}
            placeholder={settings.claude_key_added ? "Saved key is hidden" : "sk-ant-..."}
          />
          <Button type="submit" loading={saving}>
            Save settings
          </Button>
        </form>
      </Card>

      <Card className="space-y-4">
        <div>
          <h2 className="text-base font-semibold text-gray-950">Connections</h2>
          <p className="mt-1 text-sm text-gray-600">Etsy and Claude credentials stay encrypted server-side.</p>
        </div>
        <div className="space-y-3 text-sm">
          <div className="flex items-center justify-between gap-3">
            <span className="text-gray-600">Etsy</span>
            <span className="font-semibold text-gray-950">{settings.etsy_connected ? "Connected" : "Missing"}</span>
          </div>
          <div className="flex items-center justify-between gap-3">
            <span className="text-gray-600">Claude</span>
            <span className="font-semibold text-gray-950">{settings.claude_key_added ? "Saved" : "Missing"}</span>
          </div>
          <div className="flex items-center justify-between gap-3">
            <span className="text-gray-600">Plan</span>
            <span className="font-semibold text-gray-950">{settings.plan}</span>
          </div>
        </div>
        <Button type="button" variant="secondary" onClick={connectEtsy} loading={connecting} className="w-full">
          {settings.etsy_connected ? "Reconnect Etsy" : "Connect Etsy"}
        </Button>
        <Link
          href="/upgrade"
          className="inline-flex min-h-10 w-full items-center justify-center rounded-md border border-gray-200 px-4 text-sm font-semibold text-gray-900 transition hover:bg-gray-50"
        >
          Change plan
        </Link>
      </Card>
    </div>
  );
}
