"use client";

import { AlertTriangle, Bell, CheckCircle2, CircleAlert, Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";

import { Button } from "@/components/ui/Button";
import { apiFetch } from "@/lib/api";
import type { NotificationItem } from "@/lib/types";
import { cn } from "@/lib/utils";

function timeAgo(value: string) {
  const seconds = Math.max(1, Math.floor((Date.now() - new Date(value).getTime()) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function iconFor(type: string) {
  if (type.includes("CREDITS")) return <CircleAlert className="h-4 w-4 text-red-600" />;
  if (type.includes("LISTING")) return <CheckCircle2 className="h-4 w-4 text-emerald-600" />;
  if (type.includes("TOPIC")) return <Sparkles className="h-4 w-4 text-indigo-600" />;
  return <AlertTriangle className="h-4 w-4 text-amber-600" />;
}

export function NotificationBell() {
  const router = useRouter();
  const dropdownRef = useRef<HTMLDivElement | null>(null);
  const [open, setOpen] = useState(false);
  const [count, setCount] = useState(0);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);

  async function loadCount() {
    const response = await apiFetch<{ count: number }>("/notifications/unread-count");
    setCount(response.count);
  }

  async function loadNotifications() {
    const response = await apiFetch<NotificationItem[]>("/notifications?limit=5&unread_only=true");
    setNotifications(response);
  }

  useEffect(() => {
    void loadCount().catch(() => undefined);
    const interval = window.setInterval(() => void loadCount().catch(() => undefined), 60000);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    if (open) void loadNotifications().catch(() => undefined);
  }, [open]);

  useEffect(() => {
    function onClick(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  async function markRead(notification: NotificationItem) {
    await apiFetch(`/notifications/${notification.id}/read`, { method: "POST" });
    setCount((current) => Math.max(0, current - (notification.is_read ? 0 : 1)));
    setNotifications((current) => current.map((item) => item.id === notification.id ? { ...item, is_read: true } : item));
    if (notification.action_url) {
      router.push(notification.action_url);
      setOpen(false);
    }
  }

  async function markAllRead() {
    await apiFetch("/notifications/read-all", { method: "POST" });
    setCount(0);
    setNotifications((current) => current.map((item) => ({ ...item, is_read: true })));
    toast.success("Notifications marked read");
  }

  return (
    <div ref={dropdownRef} className="relative">
      <button
        type="button"
        className="relative inline-flex h-10 w-10 items-center justify-center rounded-md border border-gray-200 bg-white text-gray-700 shadow-sm transition hover:bg-gray-50"
        onClick={() => setOpen((current) => !current)}
        aria-label="Notifications"
      >
        <Bell className="h-5 w-5" />
        {count > 0 ? (
          <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-red-600 px-1 text-[10px] font-bold text-white">
            {count > 9 ? "9+" : count}
          </span>
        ) : null}
      </button>

      {open ? (
        <div className="absolute right-0 z-50 mt-2 w-80 overflow-hidden rounded-md border border-gray-200 bg-white shadow-lg">
          <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
            <p className="text-sm font-bold text-gray-950">Notifications</p>
            <button type="button" className="text-xs font-semibold text-primary hover:text-indigo-500" onClick={markAllRead}>
              Mark all read
            </button>
          </div>
          <div className="max-h-96 overflow-y-auto">
            {notifications.length ? notifications.map((notification) => (
              <button
                key={notification.id}
                type="button"
                className={cn(
                  "flex w-full gap-3 border-b border-gray-100 px-4 py-3 text-left transition hover:bg-gray-50",
                  !notification.is_read && "bg-indigo-50/60"
                )}
                onClick={() => void markRead(notification).catch(() => toast.error("Could not update notification"))}
              >
                <span className="mt-1 shrink-0">{iconFor(notification.type)}</span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-semibold text-gray-950">{notification.title}</span>
                  <span className="mt-0.5 block truncate text-xs text-gray-600">{notification.message}</span>
                  <span className="mt-1 block text-xs font-medium text-gray-400">{timeAgo(notification.created_at)}</span>
                </span>
              </button>
            )) : (
              <div className="px-4 py-8 text-center text-sm font-medium text-gray-500">No new notifications</div>
            )}
          </div>
          <div className="border-t border-gray-100 p-3">
            <Link href="/notifications" className="block">
              <Button type="button" variant="secondary" className="w-full" onClick={() => setOpen(false)}>
                View all
              </Button>
            </Link>
          </div>
        </div>
      ) : null}
    </div>
  );
}
