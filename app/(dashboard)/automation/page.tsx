"use client";

import {
  AlertTriangle,
  Bot,
  Check,
  Clock3,
  Hand,
  Loader2,
  Pause,
  Play,
  SlidersHorizontal,
  Trash2,
  Zap
} from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";

import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { apiFetch, ApiError } from "@/lib/api";
import type { AutoMode, AutomationConfig, AutomationLog, AutomationPreview, AutomationTopic, QualityMode, SettingsResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

type Tab = "setup" | "preview" | "logs";

const qualityCosts: Record<QualityMode, number> = { FULL: 90, BALANCED: 45, FAST: 25 };
const qualityIncludes: Record<QualityMode, string[]> = {
  FULL: ["15 pages", "video", "copy", "upload"],
  BALANCED: ["8 pages", "copy", "upload", "no video"],
  FAST: ["4 pages", "copy", "upload", "no video"]
};

function emptyConfig(): AutomationConfig {
  return {
    mode: "MANUAL",
    topics_json: [],
    daily_limit: 10,
    target_min_listings: null,
    target_max_listings: null,
    quality_mode: "FULL",
    auto_quality_adjust: true,
    is_running: false,
    listings_created_today: 0,
    listings_created_total: 0,
    last_run_at: null
  };
}

function topicBadge(statusValue: AutomationTopic["status"]) {
  if (statusValue === "done") return <Badge tone="green">Done</Badge>;
  if (statusValue === "in_progress") return <Badge tone="amber">In Progress</Badge>;
  return <Badge>Pending</Badge>;
}

function eventTone(event: string) {
  if (event === "LISTING_CREATED") return "bg-emerald-50 text-emerald-700";
  if (event.includes("CREDITS") || event === "ERROR") return "bg-red-50 text-red-700";
  if (event === "QUALITY_ADJUSTED") return "bg-amber-50 text-amber-700";
  if (event === "DAILY_LIMIT_REACHED") return "bg-blue-50 text-blue-700";
  if (event === "TOPIC_AUTO_DISCOVERED") return "bg-purple-50 text-purple-700";
  return "bg-gray-100 text-gray-700";
}

export default function AutomationPage() {
  const [activeTab, setActiveTab] = useState<Tab>("setup");
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [config, setConfig] = useState<AutomationConfig>(emptyConfig());
  const [preview, setPreview] = useState<AutomationPreview | null>(null);
  const [logs, setLogs] = useState<AutomationLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [starting, setStarting] = useState(false);
  const [topicName, setTopicName] = useState("");
  const [topicDescription, setTopicDescription] = useState("");

  const canStart = settings?.plan === "PRO" || settings?.plan === "AGENCY";
  const highestListings = useMemo(() => {
    if (!preview) return 1;
    return Math.max(1, ...Object.values(preview.preview).map((item) => item.listings_possible));
  }, [preview]);

  const loadConfig = useCallback(async () => {
    const data = await apiFetch<AutomationConfig>("/automation/config");
    setConfig(data);
    return data;
  }, []);

  useEffect(() => {
    async function loadInitial() {
      setLoading(true);
      try {
        const [settingsResponse, configResponse] = await Promise.all([
          apiFetch<SettingsResponse>("/settings"),
          apiFetch<AutomationConfig>("/automation/config")
        ]);
        setSettings(settingsResponse);
        setConfig(configResponse);
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "Could not load automation settings");
      } finally {
        setLoading(false);
      }
    }
    void loadInitial();
  }, []);

  useEffect(() => {
    if (activeTab === "preview") {
      void apiFetch<AutomationPreview>("/automation/preview").then(setPreview).catch(() => toast.error("Could not load preview"));
    }
    if (activeTab === "logs") {
      void apiFetch<AutomationLog[]>("/automation/logs").then(setLogs).catch(() => toast.error("Could not load logs"));
    }
  }, [activeTab]);

  function updateConfig(next: Partial<AutomationConfig>) {
    setConfig((current) => ({ ...current, ...next }));
  }

  async function saveConfig(extra: Record<string, unknown> = {}) {
    setSaving(true);
    try {
      const response = await apiFetch<AutomationConfig>("/automation/config", {
        method: "POST",
        json: {
          mode: config.mode,
          daily_limit: config.daily_limit,
          target_min_listings: config.target_min_listings,
          target_max_listings: config.target_max_listings,
          quality_mode: config.quality_mode,
          auto_quality_adjust: config.auto_quality_adjust,
          ...extra
        }
      });
      setConfig(response);
      toast.success("Automation settings saved");
      return response;
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not save settings");
      return null;
    } finally {
      setSaving(false);
    }
  }

  async function addTopic() {
    if (!topicName.trim()) return;
    const response = await saveConfig({
      topics: [{ topic: topicName.trim(), description: topicDescription.trim() }]
    });
    if (response) {
      setTopicName("");
      setTopicDescription("");
    }
  }

  async function deleteTopic(topicId: string) {
    const response = await saveConfig({ remove_topic_id: topicId });
    if (response) toast.success("Topic removed");
  }

  async function startStop() {
    if (config.is_running) {
      setStarting(true);
      try {
        await apiFetch("/automation/stop", { method: "POST" });
        await loadConfig();
        toast.success("Auto mode paused");
      } finally {
        setStarting(false);
      }
      return;
    }

    if (config.mode === "MANUAL") return;
    if (!canStart) {
      toast.error("Upgrade to Pro to start automation");
      return;
    }

    setStarting(true);
    try {
      await apiFetch("/automation/start", { method: "POST" });
      await loadConfig();
      toast.success("Auto mode is running");
    } catch (error) {
      if (error instanceof ApiError && error.status === 403) {
        toast.error("Upgrade to Pro to start automation");
      } else {
        toast.error(error instanceof Error ? error.message : "Could not start automation");
      }
    } finally {
      setStarting(false);
    }
  }

  if (loading) {
    return <Card className="flex min-h-80 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></Card>;
  }

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-950">Automation</h1>
          <p className="mt-1 text-sm text-gray-600">Control how ListifyAI creates and uploads listings.</p>
        </div>
        {config.mode !== "MANUAL" ? (
          <Button
            type="button"
            variant={config.is_running ? "danger" : "primary"}
            loading={starting}
            disabled={!config.is_running && !canStart}
            icon={config.is_running ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
            onClick={startStop}
          >
            {config.is_running ? "Stop Auto Mode" : "Start Auto Mode"}
          </Button>
        ) : null}
      </div>

      {!canStart && config.mode !== "MANUAL" ? (
        <Card className="flex flex-col gap-3 border-amber-200 bg-amber-50 md:flex-row md:items-center md:justify-between">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 text-amber-600" />
            <div>
              <p className="font-semibold text-amber-900">Pro plan required to start automation</p>
              <p className="mt-1 text-sm text-amber-800">You can configure everything now and start after upgrading.</p>
            </div>
          </div>
          <Link href="/upgrade">
            <Button type="button" variant="secondary">Upgrade</Button>
          </Link>
        </Card>
      ) : null}

      {config.is_running ? (
        <div className="flex items-center gap-2 rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-800">
          <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-emerald-500" />
          Auto mode is running
        </div>
      ) : config.mode !== "MANUAL" ? (
        <div className="rounded-md border border-gray-200 bg-white px-4 py-3 text-sm font-semibold text-gray-600">Auto mode paused</div>
      ) : null}

      <div className="flex gap-2 border-b border-gray-200">
        {(["setup", "preview", "logs"] as Tab[]).map((tab) => (
          <button
            key={tab}
            type="button"
            className={cn(
              "px-4 py-3 text-sm font-semibold capitalize transition",
              activeTab === tab ? "border-b-2 border-primary text-primary" : "text-gray-500 hover:text-gray-900"
            )}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab === "setup" ? (
        <div className="space-y-6">
          <div className="grid gap-4 lg:grid-cols-3">
            <ModeCard mode="MANUAL" current={config.mode} icon={<Hand />} title="Manual" onSelect={() => updateConfig({ mode: "MANUAL" })} />
            <ModeCard mode="AUTO" current={config.mode} icon={<Bot />} title="Auto" planRestricted={!canStart} onSelect={() => updateConfig({ mode: "AUTO" })} />
            <ModeCard mode="HYBRID" current={config.mode} icon={<SlidersHorizontal />} title="Hybrid" planRestricted={!canStart} onSelect={() => updateConfig({ mode: "HYBRID" })} />
          </div>

          {config.mode !== "MANUAL" ? (
            <>
              <Card className="space-y-5">
                <div>
                  <h2 className="text-base font-semibold text-gray-950">Your Topic List</h2>
                  <p className="mt-1 text-sm text-gray-600">New topics are appended and stay shared across Auto and Hybrid.</p>
                </div>
                <div className="grid gap-3 lg:grid-cols-[minmax(0,0.75fr)_minmax(0,1fr)_auto] lg:items-end">
                  <Input label="Topic name" name="topic" value={topicName} onChange={(event) => setTopicName(event.target.value)} placeholder="Ramadan Prayer Tracker" />
                  <label className="block" htmlFor="topic-description">
                    <span className="mb-2 block text-sm font-medium text-gray-800">Describe it</span>
                    <textarea
                      id="topic-description"
                      className="min-h-11 w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm text-gray-950 outline-none transition placeholder:text-gray-400 focus:border-primary focus:ring-2 focus:ring-indigo-500"
                      value={topicDescription}
                      onChange={(event) => setTopicDescription(event.target.value)}
                      placeholder="Printable A4 tracker with geometric border, green and gold colors"
                    />
                  </label>
                  <Button type="button" onClick={addTopic} loading={saving} icon={<Check className="h-4 w-4" />}>Add Topic</Button>
                </div>
                <div className="divide-y divide-gray-100 rounded-md border border-gray-100">
                  {config.topics_json.length ? config.topics_json.map((topic) => (
                    <div key={topic.id} className="grid gap-3 px-4 py-3 sm:grid-cols-[minmax(0,1fr)_auto_auto] sm:items-center">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-gray-950">{topic.topic}</p>
                        <p className="mt-1 line-clamp-1 text-sm text-gray-500">{topic.description || "No description"}</p>
                      </div>
                      {topicBadge(topic.status)}
                      <Button type="button" variant="ghost" className="justify-start text-red-600 hover:bg-red-50" icon={<Trash2 className="h-4 w-4" />} onClick={() => deleteTopic(topic.id)}>
                        Delete
                      </Button>
                    </div>
                  )) : (
                    <div className="px-4 py-8 text-center text-sm font-medium text-gray-500">No topics yet. Add some above and Claude will continue when the list runs out.</div>
                  )}
                </div>
              </Card>

              <Card className="space-y-5">
                <h2 className="text-base font-semibold text-gray-950">Settings</h2>
                <div className="grid gap-4 lg:grid-cols-2">
                  <Input label="Max listings per day" name="daily_limit" type="number" min={1} max={50} value={config.daily_limit} onChange={(event) => updateConfig({ daily_limit: Number(event.target.value) })} />
                  <div>
                    <span className="mb-2 block text-sm font-medium text-gray-800">Listing Quality</span>
                    <div className="grid gap-2 sm:grid-cols-3">
                      {(["FULL", "BALANCED", "FAST"] as QualityMode[]).map((quality) => (
                        <button
                          key={quality}
                          type="button"
                          className={cn(
                            "rounded-md border px-3 py-3 text-left text-sm transition",
                            config.quality_mode === quality ? "border-primary bg-indigo-50 text-indigo-900" : "border-gray-200 bg-white text-gray-700 hover:bg-gray-50"
                          )}
                          onClick={() => updateConfig({ quality_mode: quality })}
                        >
                          <span className="block font-bold">{quality}</span>
                          <span className="mt-1 block text-xs">{qualityCosts[quality]} credits/listing</span>
                        </button>
                      ))}
                    </div>
                  </div>
                  <label className="flex items-start gap-3 rounded-md border border-gray-200 bg-white p-4">
                    <input type="checkbox" className="mt-1 h-4 w-4" checked={config.auto_quality_adjust} onChange={(event) => updateConfig({ auto_quality_adjust: event.target.checked })} />
                    <span>
                      <span className="block text-sm font-semibold text-gray-950">Auto-adjust quality to stretch credits</span>
                      <span className="mt-1 block text-sm text-gray-600">If credits run low, automation reduces quality.</span>
                    </span>
                  </label>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <Input label="Target min" name="target_min" type="number" min={1} value={config.target_min_listings ?? ""} onChange={(event) => updateConfig({ target_min_listings: event.target.value ? Number(event.target.value) : null })} />
                    <Input label="Target max" name="target_max" type="number" min={1} value={config.target_max_listings ?? ""} onChange={(event) => updateConfig({ target_max_listings: event.target.value ? Number(event.target.value) : null })} />
                  </div>
                </div>
              </Card>
            </>
          ) : null}

          <Button type="button" loading={saving} onClick={() => void saveConfig()}>
            Save Settings
          </Button>
        </div>
      ) : null}

      {activeTab === "preview" ? (
        <div className="space-y-5">
          {!preview ? <Card className="flex min-h-48 items-center justify-center"><Loader2 className="h-5 w-5 animate-spin text-primary" /></Card> : (
            <>
              <Card className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div>
                  <h2 className="text-xl font-bold text-gray-950">How many listings can you get?</h2>
                  <p className="mt-1 text-sm text-gray-600">Current credit balance: {preview.credit_balance}</p>
                </div>
                {preview.recommendation ? (
                  <div className="rounded-md bg-indigo-50 px-4 py-3 text-sm text-indigo-900">
                    <strong>Recommended: {preview.recommendation.recommended_quality}</strong>
                    <span className="block">This gives you {preview.recommendation.listings_with_recommended} listings.</span>
                  </div>
                ) : null}
              </Card>
              {preview.recommendation?.warning ? (
                <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-medium text-amber-800">{preview.recommendation.warning}</div>
              ) : null}
              <div className="grid gap-4 lg:grid-cols-3">
                {(["FULL", "BALANCED", "FAST"] as QualityMode[]).map((quality) => {
                  const item = preview.preview[quality];
                  return (
                    <Card key={quality} className="space-y-4">
                      <div>
                        <h3 className="text-base font-bold text-gray-950">{quality}</h3>
                        <p className="text-sm text-gray-500">{item.cost_per_listing} credits per listing</p>
                      </div>
                      <p className="text-3xl font-bold text-gray-950">~{item.listings_possible}</p>
                      <div className="h-2 overflow-hidden rounded-full bg-gray-100">
                        <div className="h-full rounded-full bg-primary" style={{ width: `${(item.listings_possible / highestListings) * 100}%` }} />
                      </div>
                      <div className="space-y-2">
                        {qualityIncludes[quality].map((part) => (
                          <p key={part} className="flex items-center gap-2 text-sm text-gray-600"><Check className="h-4 w-4 text-emerald-600" />{part}</p>
                        ))}
                      </div>
                    </Card>
                  );
                })}
              </div>
            </>
          )}
        </div>
      ) : null}

      {activeTab === "logs" ? (
        <Card className="p-0">
          {logs.length ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-gray-100 text-xs uppercase text-gray-500">
                  <tr>
                    <th className="px-4 py-3">Time</th>
                    <th className="px-4 py-3">Event</th>
                    <th className="px-4 py-3">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {logs.map((log) => (
                    <tr key={log.id}>
                      <td className="whitespace-nowrap px-4 py-3 text-gray-500">{new Date(log.created_at).toLocaleString()}</td>
                      <td className="px-4 py-3"><span className={cn("rounded-full px-2.5 py-1 text-xs font-semibold", eventTone(log.event_type))}>{log.event_type}</span></td>
                      <td className="px-4 py-3 text-gray-700">{log.message}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="flex min-h-48 items-center justify-center text-sm font-medium text-gray-500">No automation activity yet. Start auto mode to see logs here.</div>
          )}
        </Card>
      ) : null}
    </div>
  );
}

function ModeCard({
  mode,
  current,
  icon,
  title,
  planRestricted,
  onSelect
}: {
  mode: AutoMode;
  current: AutoMode;
  icon: ReactNode;
  title: string;
  planRestricted?: boolean;
  onSelect: () => void;
}) {
  const selected = mode === current;
  const descriptions: Record<AutoMode, string> = {
    MANUAL: "You control everything. Generate listings one by one when you want.",
    AUTO: "Set it and forget it. System creates and uploads listings automatically.",
    HYBRID: "Auto mode with notifications. System works but keeps you informed."
  };
  const features: Record<AutoMode, string[]> = {
    MANUAL: ["Full control over every listing", "No automatic credit spending", "You approve before upload"],
    AUTO: ["Fully hands-free operation", "Claude discovers trending topics", "Respects your daily limit", "Stops when credits run out"],
    HYBRID: ["Auto generation with alerts", "Quality adjusts automatically", "Dashboard notifications", "You can pause anytime"]
  };
  return (
    <Card className={cn("space-y-4 transition", selected && "border-primary ring-2 ring-indigo-100")}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-md bg-indigo-50 text-primary">{icon}</div>
        {planRestricted && mode !== "MANUAL" ? <Badge tone="amber">Pro Plan Required</Badge> : null}
      </div>
      <div>
        <h2 className="text-lg font-bold text-gray-950">{title}</h2>
        <p className="mt-1 text-sm leading-6 text-gray-600">{descriptions[mode]}</p>
      </div>
      <div className="space-y-2">
        {features[mode].map((feature) => (
          <p key={feature} className="flex items-start gap-2 text-sm text-gray-600"><Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />{feature}</p>
        ))}
      </div>
      <Button type="button" variant={selected ? "primary" : "secondary"} className="w-full" onClick={onSelect} icon={mode === "AUTO" ? <Zap className="h-4 w-4" /> : mode === "HYBRID" ? <SlidersHorizontal className="h-4 w-4" /> : <Clock3 className="h-4 w-4" />}>
        {selected ? "Selected" : "Select"}
      </Button>
    </Card>
  );
}
