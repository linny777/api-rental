from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas
from auth import get_current_user

router = APIRouter(prefix="/apartments", tags=["Apartments"])


def _apply_filter(query, f: schemas.ApartmentFilter):
    if f.search:
        like = f"%{f.search}%"
        query = query.filter(
            models.Apartment.title.ilike(like) |
            models.Apartment.address.ilike(like) |
            models.Apartment.description.ilike(like)
        )
    if f.city:
        query = query.filter(models.Apartment.city.ilike(f"%{f.city}%"))
    if f.type:
        query = query.filter(models.Apartment.type == f.type)
    if f.min_rooms is not None:
        query = query.filter(models.Apartment.rooms >= f.min_rooms)
    if f.max_rooms is not None:
        query = query.filter(models.Apartment.rooms <= f.max_rooms)
    if f.min_price is not None:
        query = query.filter(models.Apartment.price >= f.min_price)
    if f.max_price is not None:
        query = query.filter(models.Apartment.price <= f.max_price)
    if f.min_area is not None:
        query = query.filter(models.Apartment.area >= f.min_area)
    if f.has_furniture is not None:
        query = query.filter(models.Apartment.has_furniture == f.has_furniture)
    if f.has_parking is not None:
        query = query.filter(models.Apartment.has_parking == f.has_parking)
    if f.pets_allowed is not None:
        query = query.filter(models.Apartment.pets_allowed == f.pets_allowed)

    sort_map = {
        "Newest": models.Apartment.created_at.desc(),
        "Oldest": models.Apartment.created_at.asc(),
        "PriceAsc": models.Apartment.price.asc(),
        "PriceDesc": models.Apartment.price.desc(),
    }
    query = query.order_by(sort_map.get(f.sort_by or "Newest", models.Apartment.created_at.desc()))
    return query


def _enrich(apt: models.Apartment) -> dict:
    """Add owner_username/owner_phone to apartment dict."""
    d = schemas.ApartmentOut.model_validate(apt).model_dump()
    if apt.owner:
        d["owner_username"] = apt.owner.username
        d["owner_phone"] = apt.owner.phone_number
    return d


@router.get("/", response_model=list[schemas.ApartmentOut])
def list_apartments(
    search: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    min_rooms: Optional[int] = Query(None),
    max_rooms: Optional[int] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    min_area: Optional[float] = Query(None),
    has_furniture: Optional[bool] = Query(None),
    has_parking: Optional[bool] = Query(None),
    pets_allowed: Optional[bool] = Query(None),
    sort_by: Optional[str] = Query("Newest"),
    available_from: Optional[datetime] = Query(None),
    available_to: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    f = schemas.ApartmentFilter(
        search=search, city=city, type=type,
        min_rooms=min_rooms, max_rooms=max_rooms,
        min_price=min_price, max_price=max_price,
        min_area=min_area, has_furniture=has_furniture,
        has_parking=has_parking, pets_allowed=pets_allowed,
        sort_by=sort_by,
        available_from=available_from,
        available_to=available_to,
    )
    from sqlalchemy.orm import joinedload
    query = db.query(models.Apartment).options(
        joinedload(models.Apartment.owner),
        joinedload(models.Apartment.images),
    ).filter(models.Apartment.is_active == True)
    query = _apply_filter(query, f)

    # Availability date filter: exclude apartments with overlapping active contracts
    if available_from is not None or available_to is not None:
        af = available_from or datetime.min
        at = available_to or datetime.max
        booked_ids = (
            db.query(models.RentalContract.apartment_id)
            .filter(
                models.RentalContract.is_terminated == False,
                models.RentalContract.is_signed == True,
                models.RentalContract.start_date < at,
                models.RentalContract.end_date > af,
            )
            .subquery()
        )
        query = query.filter(~models.Apartment.id.in_(booked_ids))

    apts = query.all()
    return [_enrich(a) for a in apts]


@router.get("/my", response_model=list[schemas.ApartmentOut])
def my_listings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    from sqlalchemy.orm import joinedload
    apts = db.query(models.Apartment).options(
        joinedload(models.Apartment.owner),
        joinedload(models.Apartment.images),
    ).filter(models.Apartment.owner_id == current_user.id).all()
    return [_enrich(a) for a in apts]


@router.get("/{apartment_id}/bookings", response_model=list[schemas.BookingPeriodOut])
def get_apartment_bookings(apartment_id: int, db: Session = Depends(get_db)):
    """Return occupied date ranges for a given apartment (signed, non-terminated contracts)."""
    contracts = (
        db.query(models.RentalContract)
        .filter(
            models.RentalContract.apartment_id == apartment_id,
            models.RentalContract.is_terminated == False,
            models.RentalContract.is_signed == True,
        )
        .all()
    )
    return [{"start_date": c.start_date, "end_date": c.end_date} for c in contracts]


@router.get("/{apartment_id}", response_model=schemas.ApartmentOut)
def get_apartment(apartment_id: int, db: Session = Depends(get_db)):
    from sqlalchemy.orm import joinedload
    apt = db.query(models.Apartment).options(
        joinedload(models.Apartment.owner),
        joinedload(models.Apartment.images),
    ).filter(models.Apartment.id == apartment_id).first()
    if not apt:
        raise HTTPException(404, "Apartment not found")
    return _enrich(apt)


def _save_images(db, apt_id: int, image_paths: list[str]):
    db.query(models.ApartmentImage).filter(
        models.ApartmentImage.apartment_id == apt_id
    ).delete()
    for i, path in enumerate(image_paths):
        db.add(models.ApartmentImage(
            apartment_id=apt_id,
            image_path=path,
            is_main=(i == 0),
        ))


@router.post("/", response_model=schemas.ApartmentOut, status_code=201)
def create_apartment(
    body: schemas.ApartmentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    data = body.model_dump(exclude={"image_paths"})
    apt = models.Apartment(**data, owner_id=current_user.id)
    db.add(apt)
    db.commit()
    db.refresh(apt)
    if body.image_paths:
        _save_images(db, apt.id, body.image_paths)
        db.commit()
    from sqlalchemy.orm import joinedload
    apt = db.query(models.Apartment).options(
        joinedload(models.Apartment.owner),
        joinedload(models.Apartment.images),
    ).filter(models.Apartment.id == apt.id).first()
    return _enrich(apt)


@router.put("/{apartment_id}", response_model=schemas.ApartmentOut)
def update_apartment(
    apartment_id: int,
    body: schemas.ApartmentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    apt = db.query(models.Apartment).filter(models.Apartment.id == apartment_id).first()
    if not apt:
        raise HTTPException(404, "Apartment not found")
    if apt.owner_id != current_user.id:
        raise HTTPException(403, "Not your apartment")

    for k, v in body.model_dump(exclude={"image_paths"}, exclude_unset=True).items():
        setattr(apt, k, v)
    if body.image_paths:
        _save_images(db, apt.id, body.image_paths)
    db.commit()
    from sqlalchemy.orm import joinedload
    apt = db.query(models.Apartment).options(
        joinedload(models.Apartment.owner),
        joinedload(models.Apartment.images),
    ).filter(models.Apartment.id == apartment_id).first()
    return _enrich(apt)


@router.patch("/{apartment_id}/toggle", response_model=schemas.ApartmentOut)
def toggle_active(
    apartment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    apt = db.query(models.Apartment).filter(models.Apartment.id == apartment_id).first()
    if not apt:
        raise HTTPException(404, "Apartment not found")
    if apt.owner_id != current_user.id:
        raise HTTPException(403, "Not your apartment")
    apt.is_active = not apt.is_active
    db.commit()
    db.refresh(apt)
    return apt


@router.delete("/{apartment_id}", status_code=204)
def delete_apartment(
    apartment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    apt = db.query(models.Apartment).filter(models.Apartment.id == apartment_id).first()
    if not apt:
        raise HTTPException(404, "Apartment not found")
    if apt.owner_id != current_user.id:
        raise HTTPException(403, "Not your apartment")
    db.delete(apt)
    db.commit()


# ── Favorites ─────────────────────────────────────────────────────────────────

@router.get("/favorites/", response_model=list[schemas.ApartmentOut])
def get_favorites(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    favs = db.query(models.Favorite).filter(models.Favorite.user_id == current_user.id).all()
    return [f.apartment for f in favs if f.apartment]


@router.post("/{apartment_id}/favorite", status_code=204)
def toggle_favorite(
    apartment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    fav = db.query(models.Favorite).filter(
        models.Favorite.user_id == current_user.id,
        models.Favorite.apartment_id == apartment_id,
    ).first()
    if fav:
        db.delete(fav)
    else:
        db.add(models.Favorite(user_id=current_user.id, apartment_id=apartment_id))
    db.commit()


@router.get("/{apartment_id}/favorite", response_model=dict)
def is_favorite(
    apartment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    exists = db.query(models.Favorite).filter(
        models.Favorite.user_id == current_user.id,
        models.Favorite.apartment_id == apartment_id,
    ).first() is not None
    return {"is_favorite": exists}
