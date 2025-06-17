from typing import List

from fastapi import FastAPI, Depends,Header,WebSocket,WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from .crud import update_or_create_media
from .models import User, Driver, DriverLocation,Location
from sqlalchemy.future import select
from fastapi import HTTPException, Depends
from uuid import UUID
from .schemas import AuthRequest, AuthResponse, UserCreate, UserOut, LocationOut, LocationCreate, MediaOut, \
    DriverCreate, DriverOut, TokenRequest, DriverWithTokenOut, LocationUpdateRequest, UserTokenInput, DriverTokenInput
from .auth import create_access_token, get_current_user, create_driver_access_token, decode_token, get_current_driver
from . import crud
from .admin import setup_admin
from .wesocket_manager import manager
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import joinedload

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
# @app.get("/get-eta")
# async def get_eta(
#     user_lat: float,
#     user_lon: float,
#     driver_lat: float,
#     driver_lon: float
# ):
#     try:
#         eta = await get_eta_from_openrouteservice(user_lat, user_lon, driver_lat, driver_lon)
#         return {"eta_minutes": eta}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
#
DEFAULT_ETA_MINUTES = 100  # fallback ETA in minutes
# @app.post("/me/location")
# async def set_or_update_location(
#     location_data: LocationCreate,
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     media_id = await crud.create_or_update_location(db, current_user.id, location_data)
#
#     # Get driver
#     result = await db.execute(select(Driver).where(Driver.id == 2))
#     print(result,"result")
#     driver = result.scalar_one_or_none()
#     print(driver.id,"driver id")
#     if not driver:
#         raise HTTPException(status_code=404, detail="Driver not found")
#
#     # Get user location
#     user_result = await db.execute(select(Location).where(Location.user_id == current_user.id))
#     user_location = user_result.scalar_one_or_none()
#     print(user_location,"user loc")
#     if not user_location:
#         raise HTTPException(status_code=404, detail="User location not found")
#
#     # Get driver location
#     driver_result = await db.execute(select(DriverLocation).where(DriverLocation.driver_id == driver.id))
#     print(driver_result,"drive result")
#     driver_location = driver_result.scalar_one_or_none()
#     print(driver_location, "driv loc")
#     if not driver_location:
#         raise HTTPException(status_code=404, detail="Driver location not found")
#
#     # Calculate ETA
#     try:
#         print("in of tryy")
#         eta = await get_eta_from_openrouteservice(
#             user_location.latitude,
#             user_location.longitude,
#             driver_location.latitude,
#             driver_location.longitude
#             # 10.1000, 76.3500,  # user latitude, longitude
#             # 9.9700, 76.2800  # driver latitude, longitude
#         )
#         print("try end")
#     except Exception as e:
#         print(f"ETA calculation error: {e}")
#         eta = DEFAULT_ETA_MINUTES  # fallback
#
#     return {
#         "first_name": driver.first_name,
#         "mobile": driver.mobile,
#         "ambulance_number": driver.ambulance_number,
#         "media_id": media_id,
#         "eta_minutes": eta,
#     }

@app.post("/me/location")
async def set_or_update_location(
        location_data: LocationCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    media_id = await crud.create_or_update_location(db, current_user.id, location_data)
    result = await db.execute(
        select(Driver).options(joinedload(Driver.location)).where(Driver.is_available == True)
    )
    drivers: List[Driver] = result.scalars().all()

    if not drivers:
        raise HTTPException(status_code=404, detail="No available drivers found")

    # Get user location
    user_result = await db.execute(select(Location).where(Location.user_id == current_user.id))
    user_location = user_result.scalar_one_or_none()
    print(user_location, "user loc")
    if not user_location:
        raise HTTPException(status_code=404, detail="User location not found")

    # Get driver location
    driver_eta_list = []

    for driver in drivers:
        if not driver.location:
            continue  # skip if location is not available

        try:
            eta = await get_eta_from_openrouteservice(
                user_location.latitude, user_location.longitude,
                driver.location.latitude, driver.location.longitude
            )
        except Exception as e:
            print(f"Error calculating ETA for driver {driver.id}: {e}")
            eta = DEFAULT_ETA_MINUTES

        driver_eta_list.append({
            "driver_id": driver.id,
            "first_name": driver.first_name,
            "mobile": driver.mobile,
            "ambulance_number": driver.ambulance_number,
            "eta_minutes": eta
        })
    if not driver_eta_list:
        raise HTTPException(status_code=404, detail="No driver locations available")

    # Sort by ETA ascending
    sorted_drivers = sorted(driver_eta_list, key=lambda x: x["eta_minutes"])
    print(sorted_drivers,"sorted drivers")
    best_driver = sorted_drivers[0]
    print(best_driver,"best_drivers")

    return best_driver

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


# @app.post("/drivers", response_model=DriverOut)
# async def register_driver(driver: DriverCreate, db: AsyncSession = Depends(get_db)):
#     existing = await crud.get_driver_by_mobile(db, driver.mobile)
#     if existing:
#         raise HTTPException(status_code=400, detail="Mobile number already exists")
#
#     return await crud.create_driver(db, driver)

@app.post("/drivers", response_model=DriverWithTokenOut)
async def register_driver(driver: DriverCreate, db: AsyncSession = Depends(get_db)):
    existing = await crud.get_driver_by_mobile(db, driver.mobile)
    if existing:
        raise HTTPException(status_code=400, detail="Mobile number already exists")

    new_driver = await crud.create_driver(db, driver)

    # Create JWT token
    access_token = create_driver_access_token(
        driver_id=new_driver.id,
        mobile=new_driver.mobile,
        ambulance_number=new_driver.ambulance_number
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "driver": new_driver
    }



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


@app.post("/driver/location")
async def update_driver_location(
    data: LocationUpdateRequest,
    db: AsyncSession = Depends(get_db),
    driver = Depends(get_current_driver)
):
    lat = data.latitude
    lon = data.longitude

    # Check if record exists
    result = await db.execute(
        select(DriverLocation).where(DriverLocation.driver_id == driver.id)
    )
    loc = result.scalar_one_or_none()

    if loc:
        loc.latitude = lat
        loc.longitude = lon
    else:
        loc = DriverLocation(
            driver_id=driver.id,
            latitude=lat,
            longitude=lon
        )
        db.add(loc)

    await db.commit()
    return {"status": "Location updated"}



@app.post("/auth/driver-login", response_model=AuthResponse)
async def driver_login(
    data: AuthRequest,
    db: AsyncSession = Depends(get_db),
    authorization: str = Header(default=None)
):
    # ✅ Token provided
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        try:
            result = await decode_token(token, db, model=Driver)

            if isinstance(result, Driver):
                return AuthResponse(access_token=token)

            if isinstance(result, dict) and result.get("expired"):
                driver = result["user"]
                new_token = create_driver_access_token(
                    driver_id=driver.id,
                    mobile=driver.mobile,
                    ambulance_number=driver.ambulance_number
                )
                return AuthResponse(
                    access_token=new_token,
                    message="Token expired. New token issued."
                )

        except HTTPException as e:
            if e.status_code == 401:
                return AuthResponse(message="Invalid or expired token")

    # 🔁 Fallback to phone login
    result = await db.execute(select(Driver).where(Driver.mobile == data.phone_number))
    driver = result.scalar_one_or_none()

    if driver:
        new_token = create_driver_access_token(
            driver_id=driver.id,
            mobile=driver.mobile,
            ambulance_number=driver.ambulance_number
        )
        return AuthResponse(
            access_token=new_token,
            message="New login token issued."
        )

    raise HTTPException(status_code=404, detail="Driver not found")

import httpx

ORS_API_KEY = "5b3ce3597851110001cf62483670764117264d618322ac641fb0f58c"

async def get_eta_from_openrouteservice(user_lat, user_lon, driver_lat, driver_lon):
    url = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
    headers = {
        "Authorization": ORS_API_KEY,
        "Content-Type": "application/json"
    }
    body = {
        "coordinates": [
            [driver_lon, driver_lat],  # Origin
            [user_lon, user_lat]       # Destination
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=body, headers=headers)

    if response.status_code == 200:
        data = response.json()
        duration_seconds = data["features"][0]["properties"]["summary"]["duration"]
        eta_minutes = round(duration_seconds / 60)
        return eta_minutes
    else:
        raise Exception(f"ORS Error: {response.status_code} {response.text}")


@app.post("/test/generate-driver-token")
async def generate_driver_token(data: DriverTokenInput):
    token = create_driver_access_token(
        driver_id=data.driver_id,
        mobile=data.mobile,
        ambulance_number=data.ambulance_number
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "note": "This token is for testing purposes only"
    }



@app.post("/test/generate-user-token")
async def generate_user_token(data: UserTokenInput):
    token = create_access_token(
        user_id=data.user_id,
        user_mobile=data.user_mobile
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "note": "This token is for testing purposes only"
    }
