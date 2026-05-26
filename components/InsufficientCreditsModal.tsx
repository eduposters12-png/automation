"use client";

import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";

type InsufficientCreditsModalProps = {
  isOpen: boolean;
  onClose: () => void;
  required: number;
  balance: number;
  action: string;
};

function formatAction(action: string) {
  return action
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function InsufficientCreditsModal({
  isOpen,
  onClose,
  required,
  balance,
  action
}: InsufficientCreditsModalProps) {
  const router = useRouter();

  return (
    <Modal open={isOpen} title="Not Enough Credits" onClose={onClose}>
      <div className="space-y-4">
        <p className="text-sm leading-6 text-gray-600">
          This action requires {required} credits but you only have {balance} credits.
        </p>
        <p className="rounded-md bg-gray-50 px-3 py-2 text-sm font-semibold text-gray-700">
          {formatAction(action)}
        </p>
        <div className="flex flex-col gap-2 sm:flex-row sm:justify-end">
          <Button type="button" variant="secondary" onClick={onClose}>
            Close
          </Button>
          <Button type="button" onClick={() => router.push("/upgrade")}>
            Upgrade Plan
          </Button>
        </div>
      </div>
    </Modal>
  );
}
