import jwt
import uuid
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .models import User
from .db import get_db
from jwt import PyJWTError, ExpiredSignatureError

SECRET_KEY = "your-super-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 240

security = HTTPBearer()

def create_access_token(user_id: str,user_mobile:str):
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"user_id": user_id,"user_mobile":user_mobile, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    print("innnnnnn")
    token = credentials.credentials
    print(token,"token")
    try:
        print("in of try")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(111111)
        user_id = payload.get("user_id")
        print(user_id,"user id ")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def verify_jwt_token(token: str, db: AsyncSession) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        mobile = payload.get("user_mobile")
        if not user_id or not mobile:
            raise HTTPException(status_code=401, detail="Invalid token")

        result = await db.execute(select(User).where(User.id == user_id, User.mobile == mobile))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return user
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def decode_token(token: str, db: AsyncSession):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return await _get_user_from_payload(payload, db)
    except ExpiredSignatureError:
        # Attempt partial decode to extract user info
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
            user = await _get_user_from_payload(payload, db)
            return {"user": user, "expired": True}
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
    except PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def _get_user_from_payload(payload: dict, db: AsyncSession):
    user_id = payload.get("user_id")
    mobile = payload.get("mobile")
    if not user_id or not mobile:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    result = await db.execute(select(User).where(User.id == user_id, User.mobile == mobile))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user