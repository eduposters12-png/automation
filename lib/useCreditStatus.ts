"use client";

import { useCallback, useEffect, useState } from "react";

import { apiFetch } from "./api";
import type { CreditAlertState, CreditStatus } from "./types";

const CREDIT_STATUS_REFRESH_EVENT = "listifyai:credit-status-refresh";

export function useCreditStatus(autoCheck: boolean = true) {
  const [creditStatus, setCreditStatus] = useState<CreditStatus | null>(null);
  const [alertState, setAlertState] = useState<CreditAlertState>({ show: false, type: null });
  const [loading, setLoading] = useState(false);

  const fetchStatus = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiFetch<CreditStatus>("/stripe/credit-status");
      setCreditStatus(data);
      if (data.alert_state !== "ok") {
        setAlertState({ show: true, type: data.alert_state });
      } else {
        setAlertState({ show: false, type: null });
      }
    } catch {
      // Status checks should never block the dashboard experience.
    } finally {
      setLoading(false);
    }
  }, []);

  const refetch = useCallback(async () => {
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event(CREDIT_STATUS_REFRESH_EVENT));
      return;
    }
    await fetchStatus();
  }, [fetchStatus]);

  const dismissAlert = useCallback(() => {
    setAlertState((prev) => ({ ...prev, show: false }));
  }, []);

  useEffect(() => {
    if (autoCheck) {
      void fetchStatus();
    }
  }, [autoCheck, fetchStatus]);

  useEffect(() => {
    function refreshFromEvent() {
      void fetchStatus();
    }

    window.addEventListener(CREDIT_STATUS_REFRESH_EVENT, refreshFromEvent);
    return () => window.removeEventListener(CREDIT_STATUS_REFRESH_EVENT, refreshFromEvent);
  }, [fetchStatus]);

  return { creditStatus, alertState, dismissAlert, refetch, loading };
}
