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
  price: string | null;
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
