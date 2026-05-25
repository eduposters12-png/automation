import type { Plan } from "@/lib/types";

export const planDetails: Record<Exclude<Plan, "FREE">, {
  name: string;
  price: string;
  listings: string;
  shops: string;
  planId: string;
}> = {
  BASIC: {
    name: "Basic",
    price: "$19",
    listings: "20 listings/month",
    shops: "1 shop",
    planId: "basic"
  },
  PRO: {
    name: "Pro",
    price: "$49",
    listings: "100 listings/month",
    shops: "3 shops",
    planId: "pro"
  },
  AGENCY: {
    name: "Agency",
    price: "$99",
    listings: "Unlimited listings",
    shops: "10 shops",
    planId: "agency"
  }
};

export function formatLimit(limit: number | null) {
  return limit === null ? "Unlimited" : limit.toString();
}
