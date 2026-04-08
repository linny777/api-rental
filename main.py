import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import engine
import models
from routers import auth, apartments, chats, contracts, admin, uploads
from seed import seed

# Create all tables
models.Base.metadata.create_all(bind=engine)

# Seed demo data
seed()

app = FastAPI(
    title="ApartmentRental API",
    description=(
        "REST API для приложения аренды квартир.\n\n"
        "**Тестовые аккаунты:**\n"
        "- `demo@example.com` / `demo123`\n"
        "- `admin@example.com` / `admin123` *(доступ к /admin)*\n\n"
        "Авторизация: POST `/auth/login` → скопируй `access_token` → кнопка **Authorize** → введи токен."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Upload dir (mount happens AFTER routers — see bottom of file)
UPLOAD_DIR = "/app/data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.include_router(auth.router)
app.include_router(apartments.router)
app.include_router(chats.router)
app.include_router(contracts.router)
app.include_router(admin.router)
app.include_router(uploads.router)


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "ApartmentRental API",
        "docs": "/docs",
        "redoc": "/redoc",
    }


# Mount AFTER all routers so POST /uploads/image is handled by the router first
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
