export type Plan = "FREE" | "BASIC" | "PRO" | "AGENCY";

export type User = {
  id: string;
  email: string;
  name: string;
  plan: Plan;
  credit_balance: number;
  days_until_reset: number | null;
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
  claude_key_last4?: string | null;
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
  claude_key_last4?: string | null;
};

export type UsageAction = "IMAGE_GENERATED" | "VIDEO_GENERATED" | "LISTING_UPLOADED";

export type UsageWithLimit = {
  used: number;
  limit: number;
};

export type AnalyticsDashboard = {
  total_listings: number;
  live_listings: number;
  usage_this_month: Record<UsageAction, UsageWithLimit>;
  plan: Plan;
  recent_listings: {
    id: string;
    title: string | null;
    status: Listing["status"];
    primary_image_url: string | null;
    created_at: string;
  }[];
  shop: {
    niche: string | null;
    last_analyzed_at: string | null;
  };
};

export type AnalyticsUsageResponse = {
  usage: Record<UsageAction, number>;
  usage_with_limits: Record<UsageAction, UsageWithLimit>;
  plan: Plan;
};

export interface CreditBalance {
  credit_balance: number;
  plan: string;
}

export interface CreditHistoryEntry {
  action: string;
  credits_delta: number;
  balance_after: number;
  created_at: string;
  listing_id: string | null;
}

export interface CreditStatus {
  alert_state: "ok" | "software_low" | "software_depleted" | "claude_depleted" | "both_depleted";
  software_credits: {
    balance: number;
    plan_total: number;
    percent_remaining: number;
    depleted: boolean;
    low: boolean;
    days_until_reset: number | null;
    reset_at: string | null;
  };
  claude: {
    working: boolean;
    status: string;
    message: string;
  };
  plan: string;
  cycle_end: string | null;
  days_until_reset: number | null;
}

export interface CreditAlertState {
  show: boolean;
  type: "software_low" | "software_depleted" | "claude_depleted" | "both_depleted" | null;
}

export type TestConnectionResponse = {
  success: boolean;
  message: string;
};

export type ProductPotential = "High" | "Medium" | "Low";

export type ShopOpportunity = {
  title: string;
  description: string;
};

export type ProductIdea = {
  title: string;
  descriptionIdea: string;
  targetKeywords: string[];
  suggestedPrice: number;
  potential: ProductPotential;
  rationale: string;
};

export type ShopAnalysis = {
  niche: string;
  style: string;
  strengths: string[];
  opportunities: ShopOpportunity[];
  productIdeas: ProductIdea[];
};

export type ShopAnalysisResponse = {
  analyzed: boolean;
  analysis?: ShopAnalysis | null;
  last_analyzed_at?: string | null;
};

export type Listing = {
  id: string;
  status: "DRAFT" | "QUEUED" | "QUEUED_MANUAL" | "IMAGE_APPROVED" | "COPY_READY" | "READY_TO_UPLOAD" | "LIVE" | "FAILED";
  image_urls: string[];
  primary_image_url: string | null;
  image_prompt: string | null;
  claude_review_json: ClaudeImageReview | null;
  video_url: string | null;
  title: string | null;
  description: string | null;
  tags: string[];
  price: number | null;
  is_bundle: boolean;
  etsy_listing_id: string | null;
  error_message: string | null;
  created_at: string;
};

export type ClaudeImageReview = {
  approved: boolean;
  feedback: string;
  improvedPrompt: string;
};

export type ImageGenerationResponse = {
  listing_id: string;
  image_url: string;
  claude_review: ClaudeImageReview;
  image_urls: string[];
  review_unavailable: boolean;
};

export type RegenerateImageResponse = {
  image_url: string;
  claude_review: ClaudeImageReview;
  image_urls: string[];
  review_unavailable: boolean;
};

export type HighResImageResponse = {
  image_url: string;
  image_urls: string[];
};

export type ApproveImageResponse = {
  success: boolean;
};

export type GenerateVideoResponse = {
  video_url: string;
};

export type GenerateCopyResponse = {
  title: string;
  description: string;
  tags: string[];
  suggestedPrice: number;
};

export type ListingPackage = {
  listing_id: string;
  image_urls: string[];
  primary_image_url: string | null;
  pdf_url: string | null;
  video_url: string | null;
  title: string | null;
  description: string | null;
  tags: string[];
  price: number | null;
  status: Listing["status"];
  is_bundle: boolean;
};

export type SuccessResponse = {
  success: boolean;
};

export type ListingUploadResponse = {
  success: boolean;
  message: string;
  job_id: string | null;
};

export type ListingStatusResponse = {
  status: Listing["status"];
  etsy_listing_id: string | null;
  etsy_listing_url: string | null;
  error_message: string | null;
};

export type PaginatedListingsResponse = {
  listings: Listing[];
  total: number;
  page: number;
  per_page: number;
};

export type BulkQueueResponse = {
  queued_count: number;
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

export interface EtsyConnectionStatus {
  connected: boolean;
  shop_name: string | null;
  shop_url: string | null;
  etsy_shop_id: string | null;
  connected_at: string | null;
}

export type AutoMode = "MANUAL" | "AUTO" | "HYBRID";
export type QualityMode = "FULL" | "BALANCED" | "FAST";

export type AutomationTopic = {
  id: string;
  topic: string;
  description: string;
  status: "pending" | "in_progress" | "done";
  listing_id?: string;
};

export type AutomationConfig = {
  mode: AutoMode;
  topics_json: AutomationTopic[];
  daily_limit: number;
  target_min_listings: number | null;
  target_max_listings: number | null;
  quality_mode: QualityMode;
  auto_quality_adjust: boolean;
  is_running: boolean;
  listings_created_today: number;
  listings_created_total: number;
  last_run_at: string | null;
};

export type AutomationPreview = {
  credit_balance: number;
  preview: Record<QualityMode, {
    quality_mode: QualityMode;
    cost_per_listing: number;
    listings_possible: number;
    credit_balance: number;
    credits_needed_for_one: number;
  }>;
  recommendation: {
    recommended_quality: QualityMode;
    listings_with_recommended: number;
    can_hit_target: boolean;
    warning: string | null;
  } | null;
  current_quality: QualityMode;
  target_min: number | null;
  target_max: number | null;
};

export type AutomationLog = {
  id: string;
  event_type: string;
  message: string;
  metadata_json: Record<string, unknown>;
  created_at: string;
};

export type NotificationItem = {
  id: string;
  type: string;
  title: string;
  message: string;
  is_read: boolean;
  action_url: string | null;
  metadata_json: Record<string, any>;
  created_at: string;
};
