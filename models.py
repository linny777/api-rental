from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, LargeBinary, Numeric, String, Text
)
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), nullable=False)
    email = Column(String(200), unique=True, nullable=False, index=True)
    password_hash = Column(String(200), nullable=False)
    phone_number = Column(String(20), nullable=True)
    avatar_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    apartments = relationship("Apartment", back_populates="owner", foreign_keys="Apartment.owner_id")
    favorites = relationship("Favorite", back_populates="user")
    owned_chats = relationship("Chat", back_populates="owner", foreign_keys="Chat.owner_id")
    rented_chats = relationship("Chat", back_populates="renter", foreign_keys="Chat.renter_id")
    messages = relationship("Message", back_populates="sender")
    owned_contracts = relationship("RentalContract", back_populates="owner", foreign_keys="RentalContract.owner_id")
    rented_contracts = relationship("RentalContract", back_populates="renter", foreign_keys="RentalContract.renter_id")


class Apartment(Base):
    __tablename__ = "apartments"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    address = Column(String(300), nullable=False)
    city = Column(String(100), nullable=False)
    rooms = Column(Integer, nullable=False)
    area = Column(Float, nullable=False)
    floor = Column(Integer, nullable=True)
    total_floors = Column(Integer, nullable=True)
    type = Column(String(20), nullable=False, default="Rent")       # Rent | Sale
    deal_type = Column(String(20), nullable=False, default="LongTerm")  # LongTerm | ShortTerm | Daily
    has_furniture = Column(Boolean, default=False)
    has_parking = Column(Boolean, default=False)
    pets_allowed = Column(Boolean, default=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="apartments", foreign_keys=[owner_id])
    images = relationship("ApartmentImage", back_populates="apartment", cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="apartment", cascade="all, delete-orphan")
    chats = relationship("Chat", back_populates="apartment", cascade="all, delete-orphan")
    contracts = relationship("RentalContract", back_populates="apartment")
    blocked_periods = relationship("BlockedPeriod", back_populates="apartment", cascade="all, delete-orphan")


class ApartmentImage(Base):
    __tablename__ = "apartment_images"

    id = Column(Integer, primary_key=True, index=True)
    apartment_id = Column(Integer, ForeignKey("apartments.id"), nullable=False)
    image_path = Column(String(500), nullable=False)
    is_main = Column(Boolean, default=False)

    apartment = relationship("Apartment", back_populates="images")


class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    apartment_id = Column(Integer, ForeignKey("apartments.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="favorites")
    apartment = relationship("Apartment", back_populates="favorites")


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    apartment_id = Column(Integer, ForeignKey("apartments.id"), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    renter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    apartment = relationship("Apartment", back_populates="chats")
    owner = relationship("User", back_populates="owned_chats", foreign_keys=[owner_id])
    renter = relationship("User", back_populates="rented_chats", foreign_keys=[renter_id])
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)
    is_system = Column(Boolean, default=False)
    contract_id = Column(Integer, ForeignKey("rental_contracts.id"), nullable=True)

    chat = relationship("Chat", back_populates="messages")
    sender = relationship("User", back_populates="messages")
    contract = relationship("RentalContract", back_populates="messages")


class RentalContract(Base):
    __tablename__ = "rental_contracts"

    id = Column(Integer, primary_key=True, index=True)
    contract_number = Column(String(30), unique=True, nullable=False)
    apartment_id = Column(Integer, ForeignKey("apartments.id"), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    renter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    monthly_price = Column(Numeric(10, 2), nullable=False)
    signature_data = Column(LargeBinary, nullable=True)
    owner_signature_data = Column(LargeBinary, nullable=True)
    pdf_data = Column(LargeBinary, nullable=True)
    is_signed = Column(Boolean, default=False)
    is_owner_signed = Column(Boolean, default=False)
    is_terminated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    signed_at = Column(DateTime, nullable=True)
    owner_signed_at = Column(DateTime, nullable=True)
    terminated_at = Column(DateTime, nullable=True)

    apartment = relationship("Apartment", back_populates="contracts")
    owner = relationship("User", back_populates="owned_contracts", foreign_keys=[owner_id])
    renter = relationship("User", back_populates="rented_contracts", foreign_keys=[renter_id])
    messages = relationship("Message", back_populates="contract")

    @property
    def is_fully_signed(self) -> bool:
        return self.is_signed and self.is_owner_signed


class BlockedPeriod(Base):
    """Date ranges manually blocked by the apartment owner (no contract required)."""
    __tablename__ = "blocked_periods"

    id = Column(Integer, primary_key=True, index=True)
    apartment_id = Column(Integer, ForeignKey("apartments.id"), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    reason = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    apartment = relationship("Apartment", back_populates="blocked_periods")
