"use client";

import { AlertTriangle, CheckCircle2, CircleAlert, Loader2, Sparkles, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { apiFetch } from "@/lib/api";
import type { NotificationItem } from "@/lib/types";
import { cn } from "@/lib/utils";

function iconFor(type: string) {
  if (type.includes("CREDITS")) return <CircleAlert className="h-5 w-5 text-red-600" />;
  if (type.includes("LISTING")) return <CheckCircle2 className="h-5 w-5 text-emerald-600" />;
  if (type.includes("TOPIC")) return <Sparkles className="h-5 w-5 text-indigo-600" />;
  return <AlertTriangle className="h-5 w-5 text-amber-600" />;
}

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);

  async function loadNotifications() {
    setLoading(true);
    try {
      const response = await apiFetch<NotificationItem[]>("/notifications?limit=50");
      setNotifications(response);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not load notifications");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadNotifications();
  }, []);

  async function markRead(notification: NotificationItem) {
    await apiFetch(`/notifications/${notification.id}/read`, { method: "POST" });
    setNotifications((current) => current.map((item) => item.id === notification.id ? { ...item, is_read: true } : item));
  }

  async function markAllRead() {
    const response = await apiFetch<{ success: boolean; count: number }>("/notifications/read-all", { method: "POST" });
    setNotifications((current) => current.map((item) => ({ ...item, is_read: true })));
    toast.success(`${response.count} notifications marked read`);
  }

  async function deletePausedTopic(notification: NotificationItem) {
    const topicId = notification.metadata_json?.topic_id;
    if (!topicId) return;
    await apiFetch("/automation/config", { method: "POST", json: { remove_topic_id: topicId } });
    await markRead(notification);
    toast.success("Topic removed");
  }

  if (loading) {
    return <Card className="flex min-h-80 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></Card>;
  }

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-950">Notifications</h1>
          <p className="mt-1 text-sm text-gray-600">Automation and account updates.</p>
        </div>
        <Button type="button" variant="secondary" onClick={markAllRead}>Mark all as read</Button>
      </div>

      <div className="space-y-3">
        {notifications.length ? notifications.map((notification) => {
          const isPauseAction = notification.type === "AUTO_PAUSED" && notification.metadata_json?.actions;
          return (
            <Card key={notification.id} className={cn("flex flex-col gap-4 sm:flex-row sm:items-start", !notification.is_read && "border-indigo-200 bg-indigo-50/50")}>
              <div className="shrink-0">{iconFor(notification.type)}</div>
              <button type="button" className="min-w-0 flex-1 text-left" onClick={() => void markRead(notification)}>
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-sm font-bold text-gray-950">{notification.title}</h2>
                  {!notification.is_read ? <span className="h-2 w-2 rounded-full bg-primary" /> : null}
                </div>
                <p className="mt-1 text-sm leading-6 text-gray-600">{notification.message}</p>
                <p className="mt-2 text-xs font-medium text-gray-400">{new Date(notification.created_at).toLocaleString()}</p>
              </button>
              {isPauseAction ? (
                <div className="flex shrink-0 gap-2">
                  <Button type="button" variant="danger" icon={<Trash2 className="h-4 w-4" />} onClick={() => void deletePausedTopic(notification)}>
                    Delete
                  </Button>
                  <Button type="button" variant="secondary" onClick={() => void markRead(notification)}>
                    Keep Paused
                  </Button>
                </div>
              ) : null}
            </Card>
          );
        }) : (
          <Card className="flex min-h-48 items-center justify-center text-sm font-medium text-gray-500">No notifications yet.</Card>
        )}
      </div>
    </div>
  );
}
