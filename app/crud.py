from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .models import User,Location
from fastapi import UploadFile
from app.models import MediaData
from uuid import uuid4
import os

async def get_user_by_mobile(db: AsyncSession, mobile: str):
    result = await db.execute(select(User).where(User.mobile == mobile))
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, user_data):
    new_user = User(**user_data.dict())
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

async def get_user_location(db: AsyncSession, user_id: int):
    result = await db.execute(select(Location).where(Location.user_id == user_id))
    return result.scalar_one_or_none()


async def create_or_update_location(db: AsyncSession, user_id: int, location_data):
    existing = await get_user_location(db, user_id)
    if existing:
        existing.latitude = location_data.latitude
        existing.longitude = location_data.longitude
        existing.landmark = location_data.address
    else:
        existing = Location(user_id=user_id, **location_data.dict())
        db.add(existing)

    await db.commit()
    await db.refresh(existing)
    return existing

# Get absolute path to the app directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

async def save_file(file: UploadFile, folder: str) -> str:
    ext = file.filename.split(".")[-1]
    filename = f"{uuid4()}.{ext}"

    # Construct absolute path inside app/uploads/<folder>
    relative_path = os.path.join("uploads", folder, filename)
    absolute_path = os.path.join(BASE_DIR, relative_path)

    # Ensure the folder exists
    os.makedirs(os.path.dirname(absolute_path), exist_ok=True)

    with open(absolute_path, "wb") as f:
        content = await file.read()
        f.write(content)

    return relative_path  # return relative path for storing in DB


async def get_or_create_media(db: AsyncSession, user_id: int) -> MediaData:
    result = await db.execute(select(MediaData).where(MediaData.user_id == user_id))
    media = result.scalar_one_or_none()
    if media is None:
        media = MediaData(user_id=user_id)
        db.add(media)
        await db.commit()
        await db.refresh(media)
    return media

async def upload_image(db: AsyncSession, user_id: int, image: UploadFile):
    media = await get_or_create_media(db, user_id)
    media.image_path = await save_file(image, "images")
    await db.commit()
    return media

async def upload_audio(db: AsyncSession, user_id: int, audio: UploadFile):
    media = await get_or_create_media(db, user_id)
    media.audio_path = await save_file(audio, "audio")
    await db.commit()
    return media

async def update_mobile_number(db: AsyncSession, user_id: int, mobile_number: str):
    media = await get_or_create_media(db, user_id)
    media.mobile_number = mobile_number
    await db.commit()
    return media

async def update_or_create_media(
    db: AsyncSession,
    user_id: int,
    image: UploadFile = None,
    audio: UploadFile = None,
    mobile_number: str = None
):
    from .models import MediaData

    result = await db.execute(select(MediaData).where(MediaData.user_id == user_id))
    media = result.scalar_one_or_none()

    if not media:
        media = MediaData(user_id=user_id)

    if image:
        image_path = await save_file(image, "images")
        media.image_path = image_path

    if audio:
        audio_path = await save_file(audio, "audio")
        media.audio_path = audio_path

    if mobile_number:
        media.mobile_number = mobile_number

    db.add(media)
    await db.commit()
    await db.refresh(media)

    return media
