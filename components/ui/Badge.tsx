"use client";

import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type BadgeTone = "gray" | "indigo" | "green" | "red" | "amber";

const tones: Record<BadgeTone, string> = {
  gray: "bg-gray-100 text-gray-700",
  indigo: "bg-indigo-50 text-indigo-700",
  green: "bg-emerald-50 text-emerald-700",
  red: "bg-red-50 text-red-700",
  amber: "bg-amber-50 text-amber-700"
};

type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: BadgeTone;
};

export function Badge({ className, tone = "gray", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold",
        tones[tone],
        className
      )}
      {...props}
    />
  );
}
