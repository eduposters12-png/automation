"use client";

import { CheckCircle2, ExternalLink, KeyRound, Store } from "lucide-react";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { apiFetch } from "@/lib/api";
import type { OnboardingStatus } from "@/lib/types";

export function OnboardingSteps({
  initialStatus,
  etsyResult
}: {
  initialStatus: OnboardingStatus;
  etsyResult?: string;
}) {
  const router = useRouter();
  const [status, setStatus] = useState(initialStatus);
  const [claudeKey, setClaudeKey] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [saving, setSaving] = useState(false);

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

  async function saveClaudeKey(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const claudeKey = String(formData.get("claude_api_key") || "").trim();
    if (!claudeKey) {
      if (status.complete) {
        router.push("/dashboard");
        return;
      }
      toast.error("Enter your Claude API key");
      return;
    }

    setSaving(true);
    try {
      const nextStatus = await apiFetch<OnboardingStatus>("/onboarding/claude-key", {
        method: "POST",
        json: { claude_api_key: claudeKey }
      });
      setStatus(nextStatus);
      setClaudeKey("");
      toast.success("Claude key saved");
      if (nextStatus.complete) {
        router.push("/dashboard");
        router.refresh();
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not save Claude key");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      {etsyResult === "connected" ? (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-700">
          Etsy shop connected.
        </div>
      ) : null}
      {etsyResult === "failed" || etsyResult === "invalid" || etsyResult === "denied" ? (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
          Etsy connection did not complete.
        </div>
      ) : null}

      <Card className="space-y-4">
        <div className="flex items-start gap-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-indigo-50 text-primary">
            {status.etsy_connected ? <CheckCircle2 className="h-5 w-5" /> : <Store className="h-5 w-5" />}
          </div>
          <div className="min-w-0 flex-1">
            <h2 className="text-lg font-semibold text-gray-950">Connect Etsy Shop</h2>
            <p className="mt-1 text-sm text-gray-600">
              Etsy OAuth stores access securely without asking sellers to paste API keys.
            </p>
          </div>
          <Button type="button" onClick={connectEtsy} loading={connecting} variant={status.etsy_connected ? "secondary" : "primary"}>
            {status.etsy_connected ? "Reconnect" : "Connect"}
          </Button>
        </div>
      </Card>

      <Card>
        <form className="space-y-4" onSubmit={saveClaudeKey}>
          <div className="flex items-start gap-4">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-gray-100 text-gray-700">
              {status.claude_key_added ? <CheckCircle2 className="h-5 w-5" /> : <KeyRound className="h-5 w-5" />}
            </div>
            <div className="min-w-0 flex-1 space-y-4">
              <div>
                <h2 className="text-lg font-semibold text-gray-950">Add Claude API Key</h2>
                <a
                  href="https://console.anthropic.com/"
                  target="_blank"
                  rel="noreferrer"
                  className="mt-1 inline-flex items-center gap-1 text-sm font-medium text-primary hover:text-indigo-500"
                >
                  Anthropic Console
                  <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                </a>
              </div>
              <Input
                label="Claude API key"
                name="claude_api_key"
                type="password"
                autoComplete="off"
                value={claudeKey}
                onChange={(event) => setClaudeKey(event.target.value)}
                placeholder={status.claude_key_added ? "Saved key is hidden" : "sk-ant-..."}
                required={!status.claude_key_added}
              />
            </div>
          </div>
          <div className="flex justify-end">
            <Button type="submit" loading={saving}>
              Save key
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
