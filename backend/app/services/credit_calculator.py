from backend.app.services.credit_service import CREDIT_COSTS

QUALITY_PRESETS = {
    "FULL": {"pages": 15, "images_per_page": 1, "video": True},
    "BALANCED": {"pages": 8, "images_per_page": 1, "video": False},
    "FAST": {"pages": 4, "images_per_page": 1, "video": False},
}


def cost_per_listing(quality_mode: str) -> int:
    normalized = quality_mode.upper()
    preset = QUALITY_PRESETS.get(normalized, QUALITY_PRESETS["FAST"])
    image_cost = preset["pages"] * preset["images_per_page"] * CREDIT_COSTS["IMAGE_GENERATION"]
    video_cost = CREDIT_COSTS["VIDEO_GENERATION"] if preset["video"] else 0
    return image_cost + video_cost + CREDIT_COSTS["COPY_GENERATION"] + CREDIT_COSTS["ETSY_LISTING_UPLOAD"]


def calculate_listings_possible(credit_balance: int, quality_mode: str) -> dict:
    normalized = quality_mode.upper()
    cost = cost_per_listing(normalized)
    return {
        "quality_mode": normalized,
        "cost_per_listing": cost,
        "listings_possible": credit_balance // cost,
        "credit_balance": credit_balance,
        "credits_needed_for_one": cost
    }


def suggest_quality_for_target(credit_balance: int, target_min: int, target_max: int) -> dict:
    del target_max
    for quality in ("FULL", "BALANCED", "FAST"):
        listings = credit_balance // cost_per_listing(quality)
        if listings >= target_min:
            return {
                "recommended_quality": quality,
                "listings_with_recommended": listings,
                "can_hit_target": True,
                "warning": None
            }

    listings = credit_balance // cost_per_listing("FAST")
    return {
        "recommended_quality": "FAST",
        "listings_with_recommended": listings,
        "can_hit_target": False,
        "warning": "Even FAST quality cannot hit your minimum target with the current credit balance."
    }


def get_auto_quality_adjustment(credit_balance: int, current_quality: str) -> dict:
    normalized = current_quality.upper()
    if credit_balance < 50 and normalized != "FAST":
        return {
            "should_adjust": True,
            "new_quality": "FAST",
            "reason": "critical_low",
            "notification_needed": True
        }
    if credit_balance < 150 and normalized == "FULL":
        return {
            "should_adjust": True,
            "new_quality": "BALANCED",
            "reason": "low_credits",
            "notification_needed": True
        }
    if credit_balance < 300 and normalized == "FULL":
        return {
            "should_adjust": True,
            "new_quality": "BALANCED",
            "reason": "moderate_low",
            "notification_needed": True
        }
    return {
        "should_adjust": False,
        "new_quality": normalized,
        "reason": None,
        "notification_needed": False
    }
