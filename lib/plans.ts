import type { Plan } from "@/lib/types";

export const planDetails: Record<Exclude<Plan, "FREE">, {
  name: string;
  price: string;
  listings: string;
  shops: string;
  planId: string;
  credits: string;
}> = {
  BASIC: {
    name: "Basic",
    price: "$19",
    listings: "20 listings/month",
    shops: "1 shop",
    planId: "basic",
    credits: "150 credits/month"
  },
  PRO: {
    name: "Pro",
    price: "$49",
    listings: "100 listings/month",
    shops: "3 shops",
    planId: "pro",
    credits: "600 credits/month"
  },
  AGENCY: {
    name: "Agency",
    price: "$99",
    listings: "Unlimited listings",
    shops: "10 shops",
    planId: "agency",
    credits: "2000 credits/month"
  }
};

export const planCredits: Record<Plan, string> = {
  FREE: "20 signup credits",
  BASIC: "150 credits/month",
  PRO: "600 credits/month",
  AGENCY: "2000 credits/month"
};

export function formatLimit(limit: number | null) {
  return limit === null ? "Unlimited" : limit.toString();
}
