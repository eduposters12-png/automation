from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.deps import get_current_user
from backend.app.db.session import get_db
from backend.app.models.listing import Listing
from backend.app.models.user import User
from backend.app.schemas.jobs import ListingOut
from backend.app.services.shops import get_primary_shop

router = APIRouter(prefix="/listings", tags=["listings"])


@router.get("", response_model=list[ListingOut])
def list_listings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> list[ListingOut]:
    shop = get_primary_shop(db, current_user)
    if not shop:
        return []
    listings = db.scalars(
        select(Listing).where(Listing.shop_id == shop.id).order_by(Listing.created_at.desc())
    ).all()
    return [ListingOut.model_validate(listing) for listing in listings]
