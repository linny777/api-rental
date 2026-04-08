"""Seed database with demo data on first run."""
from database import SessionLocal
import models
from auth import hash_password


def seed():
    db = SessionLocal()
    try:
        if db.query(models.User).count() > 0:
            return  # already seeded

        admin = models.User(
            username="admin",
            email="admin@example.com",
            password_hash=hash_password("admin123"),
            is_active=True,
        )
        demo = models.User(
            username="demo",
            email="demo@example.com",
            password_hash=hash_password("demo123"),
            is_active=True,
        )
        db.add_all([admin, demo])
        db.commit()
        db.refresh(admin)
        db.refresh(demo)

        apt = models.Apartment(
            title="Уютная квартира в центре",
            description="Светлая квартира с видом на парк. Рядом метро.",
            price=35000,
            address="ул. Ленина, 10",
            city="Москва",
            rooms=2,
            area=55.5,
            floor=4,
            total_floors=9,
            type="Rent",
            deal_type="LongTerm",
            has_furniture=True,
            has_parking=False,
            pets_allowed=True,
            owner_id=demo.id,
        )
        db.add(apt)
        db.commit()
        print("Database seeded: admin@example.com / admin123, demo@example.com / demo123")
    finally:
        db.close()
