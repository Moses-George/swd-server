from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..core.database import get_async_db
from ..models import User
from ..schemas import UserCreate, UserOut, Token, LoginIn
from ..core.security import hash_password, verify_password, create_token, current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=Token)
async def register(body: UserCreate, db: AsyncSession = Depends(get_async_db)):
    exists = (
        await db.execute(select(User).where(User.email == body.email))
    ).scalar_one_or_none()
    if exists:
        raise HTTPException(400, "email in use")
    u = User(email=body.email, hashed_password=hash_password(body.password))
    db.add(u)
    await db.commit()
    return Token(access_token=create_token(body.email))


@router.post("/login", response_model=Token)
async def login(body: LoginIn, db: AsyncSession = Depends(get_async_db)):
    user = (
        await db.execute(select(User).where(User.email == body.email))
    ).scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "bad credentials")
    return Token(access_token=create_token(user.email), user=user)


@router.get("/me", response_model=UserOut)
async def me(u: User = Depends(current_user)):
    return u
