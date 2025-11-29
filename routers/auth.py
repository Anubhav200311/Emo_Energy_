from fastapi import APIRouter, status,  Depends, HTTPException
from sqlalchemy.orm import Session
from schema.user import Token, UserSignup, UserLogin
from models.user import User
from utils.auth import hash_password, create_access_token, verify_password
from datetime import timedelta
from config import settings
from database import get_db


router = APIRouter(prefix="", tags=["Authentication"])

@router.post("/signup", response_model=Token, status_code= status.HTTP_201_CREATED)
async def signup(user: UserSignup, db: Session = Depends(get_db)):   # read about sessions
    """Register a new user."""
    existing_user = db.query(User).filter(User.user_id == UserSignup.user_id).first()

    if existing_user:
        raise HTTPException(
            status_code= status.HTTP_400_BAD_REQUEST,
            detail= "User already exists"
        )
    
    hashed_password = hash_password(UserSignup.password)
    new_user = User(
        user_id = UserSignup.user_id,
        hashed_password = hashed_password,
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    accesss_token_expires = timedelta(minutes= settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data = {"sub" : UserSignup.user_id}, expires_delta = accesss_token_expires)

    return {"access_token": access_token, "token_type": "bearer"} # read about bearer tokens

    
@router.post("/login", response_model= Token, status_code= status.HTTP_200_OK)
async def login(user: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return access token."""    
    
    user = db.query(User).filter(User.user_id == UserLogin.user_id).first()

    if not user or not verify_password(plain_password= UserLogin.password, hashed_password=user.hashed_password):
        raise HTTPException(
            status_code= status.HTTP_401_UNAUTHORIZED,
            detail= "Incorrect user_id or password"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.user_id}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

