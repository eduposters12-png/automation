import { cookies } from "next/headers";

import { API_URL } from "@/lib/api";
import type {
  AuthResponse,
  DashboardStats,
  Job,
  OnboardingStatus,
  PaginatedListingsResponse,
  SettingsResponse
} from "@/lib/types";

async function serverApiFetch<T>(path: string): Promise<T | null> {
  const cookieHeader = cookies().toString();
  const response = await fetch(`${API_URL}${path}`, {
    cache: "no-store",
    headers: cookieHeader ? { Cookie: cookieHeader } : undefined
  });

  if (!response.ok) {
    return null;
  }
  return response.json() as Promise<T>;
}

export function getCurrentUser() {
  return serverApiFetch<AuthResponse>("/auth/me");
}

export function getDashboardStats() {
  return serverApiFetch<DashboardStats>("/dashboard/stats");
}

export function getOnboardingStatus() {
  return serverApiFetch<OnboardingStatus>("/onboarding/status");
}

export function getSettings() {
  return serverApiFetch<SettingsResponse>("/settings");
}

export function getListings() {
  return serverApiFetch<PaginatedListingsResponse>("/listings");
}

export function getJobs() {
  return serverApiFetch<Job[]>("/jobs");
}
