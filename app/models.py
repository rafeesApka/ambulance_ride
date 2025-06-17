from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from datetime import datetime
from app.db import Base
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    mobile = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    location = relationship("Location", back_populates="user", uselist=False)

    media_data = relationship("MediaData", back_populates="user", uselist=False)


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    landmark = Column(String, nullable=True)

    user = relationship("User", back_populates="location")


from sqlalchemy.dialects.postgresql import ARRAY  # PostgreSQL only

class MediaData(Base):
    __tablename__ = "media_data"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    media_id = Column(String, nullable=True, unique=True)
    mobile_number = Column(String, nullable=True)
    image_path = Column(ARRAY(String), nullable=True)  # <- changed to list
    audio_path = Column(ARRAY(String), nullable=True)

    user = relationship("User", back_populates="media_data")

# Add this to your User model:
# location = relationship("Location", back_populates="user", uselist=False)



class Driver(Base):
    __tablename__ = "drivers"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    mobile = Column(String, unique=True)
    ambulance_number = Column(String, unique=True)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    location = relationship("DriverLocation", back_populates="driver", uselist=False)


class DriverLocation(Base):
    __tablename__ = "driver_locations"
    id = Column(Integer, primary_key=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"), unique=True)
    latitude = Column(Float)
    longitude = Column(Float)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Back-reference to Driver
    driver = relationship("Driver", back_populates="location")
#
# class DriverLocation(Base):
#     __tablename__ = "driver_locations"
#     id = Column(Integer, primary_key=True)
#     driver_id = Column(Integer, ForeignKey("drivers.id"))
#     latitude = Column(Float)
#     longitude = Column(Float)
#     updated_at = Column(DateTime, default=datetime.utcnow)
#
# class Booking(Base):
#     __tablename__ = "bookings"
#     id = Column(Integer, primary_key=True)
#     user_id = Column(Integer, ForeignKey("users.id"))
#     driver_id = Column(Integer, ForeignKey("drivers.id"))
#     status = Column(String, default="pending")  # pending, accepted, completed
#     created_at = Column(DateTime, default=datetime.utcnow)