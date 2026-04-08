from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from database import get_db
import models
import schemas
from auth import get_current_user

router = APIRouter(prefix="/chats", tags=["Chats"])


def _chat_detail(chat: models.Chat, current_user_id: int, db: Session) -> schemas.ChatDetailOut:
    last_msg = (
        db.query(models.Message)
        .filter(models.Message.chat_id == chat.id)
        .order_by(models.Message.sent_at.desc())
        .first()
    )
    unread = db.query(models.Message).filter(
        models.Message.chat_id == chat.id,
        models.Message.sender_id != current_user_id,
        models.Message.is_read == False,
    ).count()
    return schemas.ChatDetailOut(
        id=chat.id,
        apartment_id=chat.apartment_id,
        owner_id=chat.owner_id,
        renter_id=chat.renter_id,
        created_at=chat.created_at,
        apartment_title=chat.apartment.title if chat.apartment else None,
        owner_username=chat.owner.username if chat.owner else None,
        renter_username=chat.renter.username if chat.renter else None,
        last_message=last_msg.content if last_msg else None,
        last_message_at=last_msg.sent_at if last_msg else None,
        unread_count=unread,
    )


def _msg_out(msg: models.Message) -> schemas.MessageOut:
    return schemas.MessageOut(
        id=msg.id,
        chat_id=msg.chat_id,
        sender_id=msg.sender_id,
        sender_username=msg.sender.username if msg.sender else None,
        content=msg.content,
        sent_at=msg.sent_at,
        is_read=msg.is_read,
        is_system=msg.is_system,
        contract_id=msg.contract_id,
    )


@router.post("/", response_model=schemas.ChatDetailOut, status_code=201)
def get_or_create_chat(
    apartment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    apt = db.query(models.Apartment).filter(models.Apartment.id == apartment_id).first()
    if not apt:
        raise HTTPException(404, "Apartment not found")
    if apt.owner_id == current_user.id:
        raise HTTPException(400, "Cannot chat with yourself")

    chat = db.query(models.Chat).options(
        joinedload(models.Chat.apartment),
        joinedload(models.Chat.owner),
        joinedload(models.Chat.renter),
    ).filter(
        models.Chat.apartment_id == apartment_id,
        models.Chat.renter_id == current_user.id,
    ).first()

    if not chat:
        chat = models.Chat(
            apartment_id=apartment_id,
            owner_id=apt.owner_id,
            renter_id=current_user.id,
        )
        db.add(chat)
        db.commit()
        db.refresh(chat)
        # reload with joins
        chat = db.query(models.Chat).options(
            joinedload(models.Chat.apartment),
            joinedload(models.Chat.owner),
            joinedload(models.Chat.renter),
        ).filter(models.Chat.id == chat.id).first()

    return _chat_detail(chat, current_user.id, db)


@router.get("/unread/count", response_model=dict)
def unread_count(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    my_chats = db.query(models.Chat).filter(
        (models.Chat.owner_id == current_user.id) |
        (models.Chat.renter_id == current_user.id)
    ).all()
    chat_ids = [c.id for c in my_chats]
    count = 0
    if chat_ids:
        count = db.query(models.Message).filter(
            models.Message.chat_id.in_(chat_ids),
            models.Message.sender_id != current_user.id,
            models.Message.is_read == False,
        ).count()
    return {"unread": count}


@router.get("/", response_model=list[schemas.ChatDetailOut])
def my_chats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    chats = db.query(models.Chat).options(
        joinedload(models.Chat.apartment),
        joinedload(models.Chat.owner),
        joinedload(models.Chat.renter),
    ).filter(
        (models.Chat.owner_id == current_user.id) |
        (models.Chat.renter_id == current_user.id)
    ).order_by(models.Chat.created_at.desc()).all()
    return [_chat_detail(c, current_user.id, db) for c in chats]


@router.get("/{chat_id}", response_model=schemas.ChatDetailOut)
def get_chat(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    chat = db.query(models.Chat).options(
        joinedload(models.Chat.apartment),
        joinedload(models.Chat.owner),
        joinedload(models.Chat.renter),
    ).filter(models.Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(404, "Chat not found")
    if chat.owner_id != current_user.id and chat.renter_id != current_user.id:
        raise HTTPException(403, "Access denied")
    return _chat_detail(chat, current_user.id, db)


@router.get("/{chat_id}/messages", response_model=list[schemas.MessageOut])
def get_messages(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    chat = db.query(models.Chat).filter(models.Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(404, "Chat not found")
    if chat.owner_id != current_user.id and chat.renter_id != current_user.id:
        raise HTTPException(403, "Access denied")

    db.query(models.Message).filter(
        models.Message.chat_id == chat_id,
        models.Message.sender_id != current_user.id,
        models.Message.is_read == False,
    ).update({"is_read": True})
    db.commit()

    msgs = db.query(models.Message).options(
        joinedload(models.Message.sender)
    ).filter(
        models.Message.chat_id == chat_id
    ).order_by(models.Message.sent_at.asc()).all()
    return [_msg_out(m) for m in msgs]


@router.post("/{chat_id}/messages", response_model=schemas.MessageOut, status_code=201)
def send_message(
    chat_id: int,
    body: schemas.SendMessageRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    chat = db.query(models.Chat).filter(models.Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(404, "Chat not found")
    if chat.owner_id != current_user.id and chat.renter_id != current_user.id:
        raise HTTPException(403, "Access denied")

    msg = models.Message(
        chat_id=chat_id,
        sender_id=current_user.id,
        content=body.content.strip(),
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    # reload with sender
    msg = db.query(models.Message).options(
        joinedload(models.Message.sender)
    ).filter(models.Message.id == msg.id).first()
    return _msg_out(msg)
