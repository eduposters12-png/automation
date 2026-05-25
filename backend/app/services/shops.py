from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.shop import Shop
from backend.app.models.user import User


def get_primary_shop(db: Session, user: User) -> Shop | None:
    return db.scalar(select(Shop).where(Shop.user_id == user.id).order_by(Shop.created_at.asc()))


def get_or_create_primary_shop(db: Session, user: User) -> Shop:
    shop = get_primary_shop(db, user)
    if shop:
        return shop

    shop = Shop(user_id=user.id)
    db.add(shop)
    db.commit()
    db.refresh(shop)
    return shop
