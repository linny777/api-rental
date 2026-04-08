import os
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from auth import get_current_user
import models

UPLOAD_DIR = "/app/data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED = {"image/jpeg", "image/png", "image/webp", "image/bmp"}

router = APIRouter(prefix="/uploads", tags=["Uploads"])


@router.post("/image", response_model=dict)
async def upload_image(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(UPLOAD_DIR, filename)

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10 MB limit
        raise HTTPException(400, "File too large (max 10 MB)")

    with open(path, "wb") as f:
        f.write(content)

    return {"url": f"/uploads/{filename}"}
