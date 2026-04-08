import base64
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from database import get_db
import models
import schemas
from auth import get_current_user

router = APIRouter(prefix="/contracts", tags=["Contracts"])


def _generate_contract_number(db: Session) -> str:
    today = datetime.utcnow().strftime("%Y%m%d")
    count = db.query(models.RentalContract).count() + 1
    return f"ДА-{today}-{count:04d}"


def _load_contract(db: Session, contract_id: int) -> models.RentalContract | None:
    return db.query(models.RentalContract).options(
        joinedload(models.RentalContract.apartment),
        joinedload(models.RentalContract.owner),
        joinedload(models.RentalContract.renter),
    ).filter(models.RentalContract.id == contract_id).first()


def _contract_out(c: models.RentalContract) -> schemas.ContractOut:
    d = schemas.ContractOut.model_validate(c).model_dump()
    d["apartment_title"] = c.apartment.title if c.apartment else None
    d["owner_username"] = c.owner.username if c.owner else None
    d["renter_username"] = c.renter.username if c.renter else None
    return schemas.ContractOut(**d)


def _find_chat(db: Session, apartment_id: int, renter_id: int) -> models.Chat | None:
    return db.query(models.Chat).filter(
        models.Chat.apartment_id == apartment_id,
        models.Chat.renter_id == renter_id,
    ).first()


def _send_system_message(db: Session, chat: models.Chat, contract: models.RentalContract, content: str):
    msg = models.Message(
        chat_id=chat.id,
        sender_id=contract.renter_id,
        content=content,
        is_system=True,
        contract_id=contract.id,
    )
    db.add(msg)


@router.post("/", response_model=schemas.ContractOut, status_code=201)
def create_contract(
    body: schemas.ContractCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    apt = db.query(models.Apartment).filter(models.Apartment.id == body.apartment_id).first()
    if not apt:
        raise HTTPException(404, "Apartment not found")
    if apt.owner_id == current_user.id:
        raise HTTPException(400, "Owner cannot rent own apartment")

    existing = db.query(models.RentalContract).filter(
        models.RentalContract.apartment_id == body.apartment_id,
        models.RentalContract.renter_id == current_user.id,
        models.RentalContract.is_terminated == False,
    ).first()
    if existing:
        raise HTTPException(400, "Active contract already exists")

    contract = models.RentalContract(
        contract_number=_generate_contract_number(db),
        apartment_id=body.apartment_id,
        owner_id=apt.owner_id,
        renter_id=current_user.id,
        start_date=body.start_date,
        end_date=body.end_date,
        monthly_price=body.monthly_price,
    )
    db.add(contract)
    db.commit()
    return _contract_out(_load_contract(db, contract.id))


class SignRequest(BaseModel):
    signature_base64: str  # PNG as base64


@router.post("/{contract_id}/sign", response_model=schemas.ContractOut)
def sign_contract(
    contract_id: int,
    body: SignRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    contract = _load_contract(db, contract_id)
    if not contract:
        raise HTTPException(404, "Contract not found")
    if contract.renter_id != current_user.id:
        raise HTTPException(403, "Only renter can sign here")
    if contract.is_signed:
        raise HTTPException(400, "Already signed by renter")

    contract.signature_data = base64.b64decode(body.signature_base64)
    contract.is_signed = True
    contract.signed_at = datetime.utcnow()

    chat = _find_chat(db, contract.apartment_id, contract.renter_id)
    if chat:
        _send_system_message(
            db, chat, contract,
            f"📄 Арендатор подписал договор {contract.contract_number}. "
            f"Срок: {contract.start_date.strftime('%d.%m.%Y')} – {contract.end_date.strftime('%d.%m.%Y')}. "
            f"Ожидается подпись арендодателя."
        )

    db.commit()
    return _contract_out(_load_contract(db, contract_id))


@router.post("/{contract_id}/sign-owner", response_model=schemas.ContractOut)
def sign_contract_owner(
    contract_id: int,
    body: SignRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    contract = _load_contract(db, contract_id)
    if not contract:
        raise HTTPException(404, "Contract not found")
    if contract.owner_id != current_user.id:
        raise HTTPException(403, "Only owner can sign here")
    if not contract.is_signed:
        raise HTTPException(400, "Renter must sign first")
    if contract.is_owner_signed:
        raise HTTPException(400, "Already signed by owner")

    contract.owner_signature_data = base64.b64decode(body.signature_base64)
    contract.is_owner_signed = True
    contract.owner_signed_at = datetime.utcnow()

    # Generate PDF now that both parties signed
    try:
        from pdf_generator import generate as gen_pdf
        contract.pdf_data = gen_pdf(contract)
    except Exception:
        pass  # PDF generation failure should not block signing

    chat = _find_chat(db, contract.apartment_id, contract.renter_id)
    if chat:
        _send_system_message(
            db, chat, contract,
            f"✅ Договор {contract.contract_number} подписан обеими сторонами. "
            f"Договор вступил в силу."
        )

    db.commit()
    return _contract_out(_load_contract(db, contract_id))


@router.post("/{contract_id}/terminate", response_model=schemas.ContractOut)
def terminate_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    contract = _load_contract(db, contract_id)
    if not contract:
        raise HTTPException(404, "Contract not found")
    if contract.owner_id != current_user.id and contract.renter_id != current_user.id:
        raise HTTPException(403, "Access denied")
    if contract.is_terminated:
        raise HTTPException(400, "Contract already terminated")

    contract.is_terminated = True
    contract.terminated_at = datetime.utcnow()

    role = "арендодатель" if contract.owner_id == current_user.id else "арендатор"
    chat = _find_chat(db, contract.apartment_id, contract.renter_id)
    if chat:
        _send_system_message(
            db, chat, contract,
            f"❌ Договор {contract.contract_number} расторгнут ({role}: {current_user.username}). "
            f"Дата расторжения: {contract.terminated_at.strftime('%d.%m.%Y')}."
        )

    db.commit()
    return _contract_out(_load_contract(db, contract_id))


@router.get("/my/renter", response_model=list[schemas.ContractOut])
def my_contracts_as_renter(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    contracts = db.query(models.RentalContract).options(
        joinedload(models.RentalContract.apartment),
        joinedload(models.RentalContract.owner),
        joinedload(models.RentalContract.renter),
    ).filter(models.RentalContract.renter_id == current_user.id).all()
    return [_contract_out(c) for c in contracts]


@router.get("/my/owner", response_model=list[schemas.ContractOut])
def my_contracts_as_owner(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    contracts = db.query(models.RentalContract).options(
        joinedload(models.RentalContract.apartment),
        joinedload(models.RentalContract.owner),
        joinedload(models.RentalContract.renter),
    ).filter(models.RentalContract.owner_id == current_user.id).all()
    return [_contract_out(c) for c in contracts]


@router.get("/{contract_id}", response_model=schemas.ContractOut)
def get_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    contract = _load_contract(db, contract_id)
    if not contract:
        raise HTTPException(404, "Contract not found")
    if contract.owner_id != current_user.id and contract.renter_id != current_user.id:
        raise HTTPException(403, "Access denied")
    return _contract_out(contract)


@router.get("/{contract_id}/pdf")
def download_pdf(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    from fastapi.responses import Response
    from pdf_generator import generate as gen_pdf
    contract = _load_contract(db, contract_id)
    if not contract:
        raise HTTPException(404, "Contract not found")
    if contract.owner_id != current_user.id and contract.renter_id != current_user.id:
        raise HTTPException(403, "Access denied")
    if not contract.is_fully_signed:
        raise HTTPException(400, "PDF not available until both parties sign")

    # Generate on-the-fly if not cached
    pdf_bytes = contract.pdf_data
    if not pdf_bytes:
        pdf_bytes = gen_pdf(contract)
        contract.pdf_data = pdf_bytes
        db.commit()

    from urllib.parse import quote
    safe_name = quote(f"{contract.contract_number}.pdf", safe="")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=\"contract_{contract.id}.pdf\"; filename*=UTF-8''{safe_name}"},
    )
