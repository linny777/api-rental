from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas
from auth import require_admin

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/stats", response_model=schemas.AdminStats)
def get_stats(db: Session = Depends(get_db), _=Depends(require_admin)):
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    return schemas.AdminStats(
        total_users=db.query(models.User).count(),
        active_users=db.query(models.User).filter(models.User.is_active == True).count(),
        total_apartments=db.query(models.Apartment).count(),
        active_apartments=db.query(models.Apartment).filter(models.Apartment.is_active == True).count(),
        rent_apartments=db.query(models.Apartment).filter(
            models.Apartment.is_active == True, models.Apartment.type == "Rent"
        ).count(),
        sale_apartments=db.query(models.Apartment).filter(
            models.Apartment.is_active == True, models.Apartment.type == "Sale"
        ).count(),
        total_chats=db.query(models.Chat).count(),
        total_contracts=db.query(models.RentalContract).count(),
        active_contracts=db.query(models.RentalContract).filter(
            models.RentalContract.is_terminated == False,
            models.RentalContract.is_signed == True,
        ).count(),
        total_messages=db.query(models.Message).count(),
        new_users_this_month=db.query(models.User).filter(
            models.User.created_at >= month_start
        ).count(),
        new_apartments_this_week=db.query(models.Apartment).filter(
            models.Apartment.created_at >= week_ago
        ).count(),
    )


@router.get("/users", response_model=list[schemas.UserOut])
def get_all_users(db: Session = Depends(get_db), _=Depends(require_admin)):
    return db.query(models.User).all()


@router.patch("/users/{user_id}/toggle", response_model=schemas.UserOut)
def toggle_user(user_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    return user


@router.get("/apartments", response_model=list[schemas.ApartmentOut])
def get_all_apartments(db: Session = Depends(get_db), _=Depends(require_admin)):
    from sqlalchemy.orm import joinedload
    from routers.apartments import _enrich
    apts = db.query(models.Apartment).options(
        joinedload(models.Apartment.owner),
        joinedload(models.Apartment.images),
    ).all()
    return [_enrich(a) for a in apts]


@router.delete("/apartments/{apartment_id}", status_code=204)
def force_delete_apartment(apartment_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    apt = db.query(models.Apartment).filter(models.Apartment.id == apartment_id).first()
    if not apt:
        raise HTTPException(404, "Apartment not found")
    apt.is_active = False
    db.commit()


@router.get("/messages/recent", response_model=list[schemas.MessageOut])
def recent_messages(db: Session = Depends(get_db), _=Depends(require_admin)):
    from sqlalchemy.orm import joinedload
    from routers.chats import _msg_out
    msgs = db.query(models.Message).options(
        joinedload(models.Message.sender)
    ).order_by(models.Message.sent_at.desc()).limit(100).all()
    return [_msg_out(m) for m in msgs]


@router.delete("/messages/{message_id}", status_code=204)
def delete_message(message_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    msg = db.query(models.Message).filter(models.Message.id == message_id).first()
    if not msg:
        raise HTTPException(404, "Message not found")
    db.delete(msg)
    db.commit()
