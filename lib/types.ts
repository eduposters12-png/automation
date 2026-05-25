export type Plan = "FREE" | "BASIC" | "PRO" | "AGENCY";

export type User = {
  id: string;
  email: string;
  name: string;
  plan: Plan;
  created_at: string;
};

export type AuthResponse = {
  user: User;
};

export type DashboardStats = {
  shop_name: string | null;
  shop_url: string | null;
  plan: Plan;
  total_listings: number;
  monthly_usage: number;
  monthly_limit: number | null;
  shop_limit: number;
  etsy_connected: boolean;
  claude_key_added: boolean;
};

export type OnboardingStatus = {
  etsy_connected: boolean;
  claude_key_added: boolean;
  complete: boolean;
};

export type SettingsResponse = {
  name: string;
  email: string;
  plan: Plan;
  shop_name: string | null;
  shop_url: string | null;
  niche: string | null;
  etsy_connected: boolean;
  claude_key_added: boolean;
};

export type Listing = {
  id: string;
  status: "DRAFT" | "QUEUED" | "LIVE" | "FAILED";
  image_urls: string[];
  video_url: string | null;
  title: string | null;
  description: string | null;
  tags: string[];
  price: string | null;
  etsy_listing_id: string | null;
  created_at: string;
};

export type Job = {
  id: string;
  type: "ANALYZE" | "GENERATE_IMAGE" | "GENERATE_VIDEO" | "UPLOAD_LISTING";
  status: "PENDING" | "RUNNING" | "DONE" | "FAILED";
  payload_json: Record<string, unknown>;
  result_json: Record<string, unknown> | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};
