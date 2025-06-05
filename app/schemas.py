from pydantic import BaseModel
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

    class Config:
        orm_mode = True

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