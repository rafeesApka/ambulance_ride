from fastapi import FastAPI, Depends,Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from .models import User
from sqlalchemy.future import select
from fastapi import HTTPException, Depends
import uuid
from .schemas import AuthRequest, AuthResponse,UserCreate, UserOut,LocationOut,LocationCreate,MediaOut
from .auth import create_access_token, get_current_user,verify_jwt_token,decode_token
from . import crud
from .admin import setup_admin
from fastapi.staticfiles import StaticFiles


app = FastAPI()
app.mount("/uploads", StaticFiles(directory="app/uploads"), name="uploads")
setup_admin(app)

@app.get("/users")
async def get_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    return result.scalars().all()

# @app.post("/auth/login", response_model=AuthResponse)
# async def login(data: AuthRequest, db: AsyncSession = Depends(get_db)):
#     result = await db.execute(select(User).where(User.mobile == data.phone_number))
#     user = result.scalar_one_or_none()
#
#     if user is None:
#         user = User(
#             phone_number=data.phone_number,
#             # user_id=str(uuid.uuid4())
#             user_id = user.id
#         )
#         db.add(user)
#         await db.commit()
#         await db.refresh(user)
#
#     token = create_access_token(user.id,user.mobile)
#     return {"access_token": token}

@app.post("/auth/login", response_model=AuthResponse)
async def login(
    data: AuthRequest,
    db: AsyncSession = Depends(get_db),
    authorization: str = Header(default=None)
):
    # ✅ Token provided
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        try:
            result = await decode_token(token, db)

            # Case 1: token is valid
            if isinstance(result, User):
                return AuthResponse(access_token=token)

            # Case 2: token is expired, user exists
            if isinstance(result, dict) and result.get("expired"):
                user = result["user"]
                new_token = create_access_token(user.id, user.mobile)
                return AuthResponse(
                    access_token=new_token,
                    message="Token expired. New token issued."
                )

        except HTTPException as e:
            if e.status_code == 401:
                return AuthResponse(message="Invalid or expired token")

    # 🔁 Fallback to phone login
    result = await db.execute(select(User).where(User.mobile == data.phone_number))
    user = result.scalar_one_or_none()

    if user:
        new_token = create_access_token(user.id, user.mobile)
        return AuthResponse(
            access_token=new_token,
            message="New login token issued."
        )
    else:
        raise HTTPException(status_code=404, detail="User not found")

@app.post("/users", response_model=AuthResponse)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    print("in of users post")
    existing = await crud.get_user_by_mobile(db, user.mobile)
    if existing:
        raise HTTPException(status_code=400, detail="Mobile number already exists")
    new_user = await crud.create_user(db, user)
    token = create_access_token(user_id=new_user.id,user_mobile = new_user.mobile)

    return {"access_token": token, "token_type": "bearer"}


@app.get("/me/location", response_model=LocationOut)
async def get_my_location(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    location = await crud.get_user_location(db, current_user.id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not set")
    return location


@app.post("/me/location", response_model=LocationOut)
async def set_or_update_location(
    location_data: LocationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    location = await crud.create_or_update_location(db, current_user.id, location_data)
    return location

from fastapi import UploadFile, File, Form

# @app.post("/me/upload/image", response_model=MediaOut)
# async def upload_image_from_mobile(
#     image: UploadFile = File(...),
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     media = await crud.upload_image(db, current_user.id, image)
#     return media
#
#
# @app.post("/me/upload/audio", response_model=MediaOut)
# async def upload_audio_from_mobile(
#     audio: UploadFile = File(...),
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     media = await crud.upload_audio(db, current_user.id, audio)
#     return media
#
#
# @app.post("/me/mobile", response_model=MediaOut)
# async def submit_mobile_number(
#     mobile_number: str = Form(...),
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     media = await crud.update_mobile_number(db, current_user.id, mobile_number)
#     return media


@app.post("/me/media", response_model=MediaOut)
async def upload_media(
    image: UploadFile = File(None),
    audio: UploadFile = File(None),
    mobile_number: str = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    media = await crud.update_or_create_media(
        db=db,
        user_id=current_user.id,
        image=image,
        audio=audio,
        mobile_number=mobile_number,
    )
    return media
