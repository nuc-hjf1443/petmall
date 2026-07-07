from fastapi import APIRouter, Depends, File, Form, UploadFile

from core.dependencies import get_current_user
from models.user import User
from services.upload_service import save_public_image


router = APIRouter(tags=["uploads"])


@router.post("/uploads/images")
async def upload_image(
    usage: str = Form(default="general"),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    return await save_public_image(file, user.id, usage)
