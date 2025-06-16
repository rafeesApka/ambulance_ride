from typing import List

from fastapi import FastAPI, Depends,Header,WebSocket,WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from .crud import update_or_create_media
from .models import User,Driver
from sqlalchemy.future import select
from fastapi import HTTPException, Depends
from uuid import UUID
from .schemas import AuthRequest, AuthResponse, UserCreate, UserOut, LocationOut, LocationCreate, MediaOut, \
    DriverCreate, DriverOut, TokenRequest
from .auth import create_access_token, get_current_user,verify_jwt_token,decode_token
from . import crud
from .admin import setup_admin
from .wesocket_manager import manager
from fastapi.staticfiles import StaticFiles


app = FastAPI()
app.mount("/uploads", StaticFiles(directory="app/uploads"), name="uploads")
setup_admin(app)

@app.get("/users")
async def get_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    return result.scalars().all()

@app.post("/generate-token")
async def generate_token(payload: TokenRequest):
    token = create_access_token(user_id=payload.user_id, user_mobile=payload.user_mobile)
    return {"access_token": token, "token_type": "bearer"}



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


@app.post("/me/location",)
async def set_or_update_location(
    location_data: LocationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    media_id = await crud.create_or_update_location(db, current_user.id, location_data)
    result = await db.execute(
        select(Driver).where(Driver.id == 1)
    )
    driver = result.scalar_one_or_none()

    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    return {
        "first_name": driver.first_name,
        "mobile": driver.mobile,
        "ambulance_number": driver.ambulance_number,
        "media_id": media_id,
        "eta_minutes": 12,
    }

from fastapi import UploadFile, File, Form



@app.post("/me/upload/image")
async def upload_image(
    images: List[UploadFile] = File(...),
    media_id: UUID = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not images or all(not img.filename for img in images):
        raise HTTPException(status_code=400, detail="At least one valid image file is required.")

    media = await update_or_create_media(
        db=db,
        user_id=current_user.id,
        images=images,
        media_id=media_id
    )
    return {"message": "Images uploaded successfully"}



@app.post("/me/upload/audio")
async def upload_audio(
    audios: List[UploadFile] = File(...),
    media_id: UUID = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not audios or all(not audio.filename for audio in audios):
        raise HTTPException(status_code=400, detail="At least one valid audio file is required.")

    media = await update_or_create_media(
        db=db,
        user_id=current_user.id,
        audios=audios,
        media_id=media_id
    )
    return {"message": "Audios uploaded successfully"}

from fastapi import Form

@app.post("/me/mobile")
async def submit_mobile_number(
    mobile_number: str = Form(...),
    media_id: UUID = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not mobile_number:
        raise HTTPException(status_code=400, detail="Mobile number is required.")

    media = await update_or_create_media(
        db=db,
        user_id=current_user.id,
        mobile_number=mobile_number,
        media_id=media_id
    )
    return {"message": "Mobile number submitted successfully"}


@app.post("/drivers", response_model=DriverOut)
async def register_driver(driver: DriverCreate, db: AsyncSession = Depends(get_db)):
    existing = await crud.get_driver_by_mobile(db, driver.mobile)
    if existing:
        raise HTTPException(status_code=400, detail="Mobile number already exists")

    return await crud.create_driver(db, driver)


@app.get("/drivers", response_model=list[DriverOut])
async def list_all_drivers(db: AsyncSession = Depends(get_db)):
    return await crud.get_all_drivers(db)


@app.websocket("/ws/driver/{driver_id}")
async def driver_ws(websocket: WebSocket, driver_id: int):
    await manager.connect(driver_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # data could be {"lat": ..., "lng": ...}
            save_driver_location(driver_id, data)
    except WebSocketDisconnect:
        manager.disconnect(driver_id)

async def notify_driver(driver_id: int, message: dict):
    await manager.send_message(driver_id, message)
