# app/db/schemas/user_schemas.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime  # For UserRead


# --- Base Schemas ---
class UserBase(BaseModel):
    email: EmailStr = Field(..., example="user@example.com")
    username: str = Field(..., min_length=3, max_length=50, example="johndoe")
    full_name: Optional[str] = Field(None, max_length=100, example="John Doe")


# --- Schemas for User Creation ---
class UserCreate(UserBase):
    password: str = Field(..., min_length=8, example="strongpassword123")


class UserCreatePasswordHashing(UserBase):  # Schema for internal use after password hashing
    hashed_password: str
    is_active: bool = True
    is_superuser: bool = False


# --- Schemas for User Reading ---
class UserRead(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    # last_login_at: Optional[datetime] = None # If you add this field

    class Config:
        from_attributes = True  # Pydantic v2 way for orm_mode


# --- Schemas for User Update ---
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, min_length=8)  # For password change
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


class UserUpdatePasswordHashing(
    BaseModel
):  # For internal use when updating with a new hashed_password
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    hashed_password: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


# --- Schemas for Login ---
class UserLoginSchema(BaseModel):
    username_or_email: str = Field(..., example="johndoe_or_user@example.com")
    password: str = Field(..., example="strongpassword123")


# You might also have a schema for the user object stored in JWT token if needed
# class UserInDB(UserRead): # Or a subset of fields
#     hashed_password: str
