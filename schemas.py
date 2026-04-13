from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict


class _Base(BaseModel):
    """Base: ORM mode + Decimal → float in JSON output."""
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={Decimal: float},
    )


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    phone_number: Optional[str] = None


class LoginRequest(BaseModel):
    email: str   # accepts username OR email
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── User ──────────────────────────────────────────────────────────────────────

class UserOut(_Base):
    id: int
    username: str
    email: str
    phone_number: Optional[str]
    avatar_path: Optional[str]
    created_at: datetime
    is_active: bool


class UpdateProfileRequest(BaseModel):
    username: Optional[str] = None
    phone_number: Optional[str] = None
    avatar_path: Optional[str] = None


# ── Apartment ─────────────────────────────────────────────────────────────────

class ApartmentImageOut(_Base):
    id: int
    image_path: str
    is_main: bool


class ApartmentCreate(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    address: str
    city: str
    rooms: int
    area: float
    image_paths: list[str] = []
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    type: str = "Rent"
    deal_type: str = "LongTerm"
    has_furniture: bool = False
    has_parking: bool = False
    pets_allowed: bool = False


class ApartmentUpdate(ApartmentCreate):
    pass


class ApartmentOut(_Base):
    id: int
    title: str
    description: Optional[str]
    price: float
    address: str
    city: str
    rooms: int
    area: float
    floor: Optional[int]
    total_floors: Optional[int]
    type: str
    deal_type: str
    has_furniture: bool
    has_parking: bool
    pets_allowed: bool
    owner_id: int
    owner_username: Optional[str] = None
    owner_phone: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    images: list[ApartmentImageOut] = []


class ApartmentFilter(BaseModel):
    search: Optional[str] = None
    city: Optional[str] = None
    type: Optional[str] = None
    min_rooms: Optional[int] = None
    max_rooms: Optional[int] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_area: Optional[float] = None
    has_furniture: Optional[bool] = None
    has_parking: Optional[bool] = None
    pets_allowed: Optional[bool] = None
    sort_by: Optional[str] = "Newest"
    available_from: Optional[datetime] = None
    available_to: Optional[datetime] = None


class BookingPeriodOut(BaseModel):
    start_date: datetime
    end_date: datetime
    type: str = "contract"   # "contract" | "blocked"
    id: Optional[int] = None  # id of BlockedPeriod (for deletion); None for contracts


class BlockedPeriodCreate(BaseModel):
    start_date: datetime
    end_date: datetime
    reason: Optional[str] = None


class BlockedPeriodOut(_Base):
    id: int
    apartment_id: int
    start_date: datetime
    end_date: datetime
    reason: Optional[str]


# ── Chat & Message ────────────────────────────────────────────────────────────

class MessageOut(_Base):
    id: int
    chat_id: int
    sender_id: int
    sender_username: Optional[str] = None
    content: str
    sent_at: datetime
    is_read: bool
    is_system: bool
    contract_id: Optional[int]


class ChatDetailOut(_Base):
    id: int
    apartment_id: int
    owner_id: int
    renter_id: int
    created_at: datetime
    apartment_title: Optional[str] = None
    owner_username: Optional[str] = None
    renter_username: Optional[str] = None
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None
    unread_count: int = 0


class ChatOut(_Base):
    id: int
    apartment_id: int
    owner_id: int
    renter_id: int
    created_at: datetime


class SendMessageRequest(BaseModel):
    content: str


# ── Contract ──────────────────────────────────────────────────────────────────

class ContractCreate(BaseModel):
    apartment_id: int
    start_date: datetime
    end_date: datetime
    monthly_price: float


class ContractOut(_Base):
    id: int
    contract_number: str
    apartment_id: int
    owner_id: int
    renter_id: int
    start_date: datetime
    end_date: datetime
    monthly_price: float
    is_signed: bool
    is_owner_signed: bool
    is_fully_signed: bool
    is_terminated: bool
    created_at: datetime
    signed_at: Optional[datetime]
    owner_signed_at: Optional[datetime]
    terminated_at: Optional[datetime]
    apartment_title: Optional[str] = None
    owner_username: Optional[str] = None
    renter_username: Optional[str] = None


# ── Admin ─────────────────────────────────────────────────────────────────────

class AdminStats(BaseModel):
    total_users: int
    active_users: int
    total_apartments: int
    active_apartments: int
    rent_apartments: int
    sale_apartments: int
    total_chats: int
    total_contracts: int
    active_contracts: int
    total_messages: int
    new_users_this_month: int
    new_apartments_this_week: int
