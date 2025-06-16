from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .models import User,Location
from fastapi import UploadFile
from app.models import MediaData,Driver
from uuid import uuid4
import os
from typing import Optional, List  # Import Optional for clarity

from .schemas import DriverCreate


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
    result = await db.execute(select(MediaData).where(MediaData.user_id == user_id))
    media = result.scalar_one_or_none()

    if not media:
        media = MediaData(user_id=user_id, media_id=str(uuid4()))
    elif not media.media_id:
        media.media_id = str(uuid4())
    if existing:
        existing.latitude = location_data.latitude
        existing.longitude = location_data.longitude
        existing.landmark = location_data.landmark
    else:
        existing = Location(user_id=user_id, **location_data.dict())
        db.add(existing)

    await db.commit()
    await db.refresh(existing)
    return media.media_id

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


from uuid import UUID
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile

async def update_or_create_media(
    db: AsyncSession,
    user_id: int,
    images: Optional[List[UploadFile]] = None,
    audios: Optional[List[UploadFile]] = None,
    mobile_number: Optional[str] = None,
    media_id: Optional[UUID] = None
):
    from .models import MediaData

    result = await db.execute(select(MediaData).where(MediaData.user_id == user_id))
    media = result.scalar_one_or_none()

    if not media:
        media = MediaData(
            user_id=user_id,
            media_id=str(media_id) if media_id else None,
        )
    elif media_id and str(media.media_id) != str(media_id):
        media.image_path = []
        media.audio_path = []
        media.mobile_number = None
        media.media_id = str(media_id)

    # if images:
    #     image_path = []
    #     for image in images:
    #         if image.filename:
    #             path = await save_file(image, "images")
    #             print(path,"image path")
    #             image_path.append(path)
    #     print(image_path,"list of paths")
    #     media.image_path = image_path
    #
    # if audios:
    #     audio_paths = []
    #     for audio in audios:
    #         if audio.filename:
    #             path = await save_file(audio, "audio")
    #             print(path,"audio path")
    #             audio_paths.append(path)
    #     media.audio_path = audio_paths
    if images:
        media.image_path = [
            await save_file(image, "images")
            for image in images if image.filename
        ]
    if audios:
        media.audio_path = [
            await save_file(audio, "audio")
            for audio in audios if audio.filename
        ]
    if mobile_number is not None:
        media.mobile_number = mobile_number
    print(type(media.image_path), media.image_path)
    db.add(media)
    await db.commit()
    await db.refresh(media)
    return media


async def get_driver_by_mobile(db: AsyncSession, mobile: str):
    result = await db.execute(select(Driver).where(Driver.mobile == mobile))
    return result.scalar_one_or_none()

async def create_driver(db: AsyncSession, driver_data: DriverCreate):
    new_driver = Driver(**driver_data.dict())
    db.add(new_driver)
    await db.commit()
    await db.refresh(new_driver)
    return new_driver

async def get_all_drivers(db: AsyncSession):
    result = await db.execute(select(Driver))
    return result.scalars().all()




