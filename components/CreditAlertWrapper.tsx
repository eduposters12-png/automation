"use client";

import { useRouter } from "next/navigation";

import { CreditAlertModal } from "@/components/CreditAlertModal";
import { useCreditStatus } from "@/lib/useCreditStatus";

export function CreditAlertWrapper() {
  const { creditStatus, alertState, dismissAlert } = useCreditStatus(true);
  const router = useRouter();

  const handleUpgrade = () => {
    router.push("/upgrade");
    dismissAlert();
  };

  return (
    <CreditAlertModal
      alertState={alertState}
      creditStatus={creditStatus}
      onDismiss={dismissAlert}
      onUpgrade={handleUpgrade}
    />
  );
}
