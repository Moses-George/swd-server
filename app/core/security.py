import sys
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .database import get_async_db
from ..models import User
from .config import settings

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(p: str) -> str:
    return pwd.hash(p)


def verify_password(p: str, h: str) -> bool:
    return pwd.verify(p, h)


def create_token(sub: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(
        {"sub": sub, "exp": exp}, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )


async def current_user(
    token: str = Depends(oauth2), db: AsyncSession = Depends(get_async_db)
) -> User:
    cred_exc = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        email = payload.get("sub")
        if not email:
            raise cred_exc
    except JWTError:
        raise cred_exc
    u = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not u:
        raise cred_exc
    return u
