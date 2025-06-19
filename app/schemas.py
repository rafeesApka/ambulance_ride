from pydantic import BaseModel,constr,Field
from typing import Optional
from datetime import datetime

class AuthRequest(BaseModel):
    phone_number: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    message: Optional[str] = None

class UserCreate(BaseModel):
    first_name: str
    last_name: str
    mobile: str

class UserOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    mobile: str
    created_at: datetime

    class Config:
        orm_mode = True

class UserLogin(BaseModel):
    first_name: str
    last_name: str
    mobile: str

# class LocationBase(BaseModel):
#     latitude: float
#     longitude: float
#     address: str | None = None

class LocationCreate(BaseModel):
    latitude: float
    longitude: float
    landmark: Optional[str] = None


class LocationOut(BaseModel):
    id: int
    media_id:str



class MediaOut(BaseModel):
    mobile_number: Optional[str]
    image_path: Optional[str]
    audio_path: Optional[str]

    class Config:
        orm_mode = True
# class DriverLogin(UserLogin):
#     ambulance_number: str

# class Token(BaseModel):
#     access_token: str
#     token_type: str
#
# class LocationUpdate(BaseModel):
#     latitude: float
#     longitude: float
#
# class BookingRequest(BaseModel):
#     user_latitude: float
#     user_longitude: float

class DriverCreate(BaseModel):
    owner_name: str
    owner_number: str
    owner_email: str
    owner_number: str
    driver_name: str
    mobile: constr(min_length=10, max_length=15)
    ambulance_number: str

class DriverOut(BaseModel):
    id: int
    owner_name: str
    owner_number: str
    owner_email: str
    owner_number: str
    driver_name: str
    mobile: str
    ambulance_number: str
    is_available: bool
    created_at: datetime

    class Config:
        orm_mode = True
class DriverWithTokenOut(BaseModel):
    access_token: str
    token_type: str
    driver: DriverOut
class TokenRequest(BaseModel):
    user_id: int
    user_mobile: str

class DriverInfo(BaseModel):
    first_name: str
    mobile: str
    ambulance_number: str
    media_id: Optional[str]
    eta_minutes: Optional[int]


    class Config:
        orm_mode = True

# from pydantic import BaseModel, Field

class LocationUpdateRequest(BaseModel):
    latitude: float = Field(..., example=10.123456)
    longitude: float = Field(..., example=76.543210)
class DriverTokenInput(BaseModel):
    driver_id: int
    mobile: str
    ambulance_number: str

class UserTokenInput(BaseModel):
    user_id: int
    user_mobile: str