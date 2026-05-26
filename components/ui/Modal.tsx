"use client";

import { X } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

type ModalProps = {
  open: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
  maxWidthClassName?: string;
};

export function Modal({ open, title, children, onClose, maxWidthClassName = "max-w-lg" }: ModalProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className={cn("w-full rounded-lg bg-white shadow-soft", maxWidthClassName)}>
        <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
          <h2 className="text-base font-semibold text-gray-950">{title}</h2>
          <Button
            type="button"
            variant="ghost"
            className="h-9 w-9 px-0"
            onClick={onClose}
            aria-label="Close modal"
            icon={<X className="h-4 w-4" aria-hidden="true" />}
          >
            <span className="sr-only">Close</span>
          </Button>
        </div>
        <div className="px-5 py-5">{children}</div>
      </div>
    </div>
  );
}
