# app/db/schemas/user_schemas.py
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator, BeforeValidator
from typing import Optional, Annotated
from datetime import datetime  # Ensure datetime is imported
import re
import bleach  # For HTML sanitization


# --- Helper Functions for BeforeValidators ---
# ... (keep existing helper functions)
def strip_string(v: str | None) -> str | None:
    if isinstance(v, str):
        return v.strip()
    return v


def string_to_lower(v: str | None) -> str | None:
    if isinstance(v, str):
        return v.lower()
    return v


def bleach_clean_text_only(v: str | None) -> str | None:
    if isinstance(v, str):
        # Allow no HTML tags, strip all tags and attributes, effectively keeping only text content.
        return bleach.clean(v, tags=[], attributes={}, strip=True)
    return v


# --- Annotated Types for Reusability and Strictness ---
# ... (keep existing annotated types)
StrippedString = Annotated[str, BeforeValidator(strip_string)]
LowerStrippedString = Annotated[
    str, BeforeValidator(strip_string), BeforeValidator(string_to_lower)
]
SanitizedFullNameString = Annotated[
    str,
    BeforeValidator(strip_string),
    BeforeValidator(bleach_clean_text_only),
]

# --- Regex Patterns ---
# ... (keep existing regex patterns)
USERNAME_REGEX = r"^[a-z0-9]+(?:[_-][a-z0-9]+)*$"
FULL_NAME_REGEX = r"^[a-zA-ZÀ-ÿ]+(?:[\s'-][a-zA-ZÀ-ÿ]+)*$"


# --- Base Schemas ---
class UserBase(BaseModel):
    email: Annotated[
        EmailStr,
        BeforeValidator(strip_string),
        BeforeValidator(string_to_lower),
        Field(max_length=254, example="user@example.com"),
    ]
    username: Annotated[
        LowerStrippedString,
        Field(
            min_length=3,
            max_length=30,
            pattern=USERNAME_REGEX,
            example="johndoe",
        ),
    ]
    full_name: Optional[
        Annotated[
            SanitizedFullNameString,
            Field(
                min_length=2,
                max_length=100,
                pattern=FULL_NAME_REGEX,
                example="John Doe",
            ),
        ]
    ] = None


# --- Schemas for User Creation ---
class UserCreate(UserBase):
    password: Annotated[
        StrippedString,
        Field(
            min_length=12,
            max_length=128,
            example="VeryStr0ngP@sswOrd!",
        ),
    ]


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
    last_login_at: Optional[datetime] = None  # <--- ADD THIS LINE

    class Config:
        from_attributes = True


# --- Schemas for User Update ---
# ... (keep existing UserUpdate schemas)
class UserUpdate(BaseModel):
    email: Optional[
        Annotated[
            EmailStr,
            BeforeValidator(strip_string),
            BeforeValidator(string_to_lower),
            Field(max_length=254),
        ]
    ] = None
    username: Optional[
        Annotated[LowerStrippedString, Field(min_length=3, max_length=30, pattern=USERNAME_REGEX)]
    ] = None
    full_name: Optional[
        Annotated[
            SanitizedFullNameString, Field(min_length=2, max_length=100, pattern=FULL_NAME_REGEX)
        ]
    ] = None
    password: Optional[Annotated[StrippedString, Field(min_length=12, max_length=128)]] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


class UserUpdatePasswordHashing(BaseModel):
    email: Optional[
        Annotated[
            EmailStr,
            BeforeValidator(strip_string),
            BeforeValidator(string_to_lower),
            Field(max_length=254),
        ]
    ] = None
    username: Optional[
        Annotated[LowerStrippedString, Field(min_length=3, max_length=30, pattern=USERNAME_REGEX)]
    ] = None
    full_name: Optional[
        Annotated[
            SanitizedFullNameString, Field(min_length=2, max_length=100, pattern=FULL_NAME_REGEX)
        ]
    ] = None
    hashed_password: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


# --- Schemas for Login ---
# ... (keep existing UserLoginSchema)
class UserLoginSchema(BaseModel):
    username_or_email: Annotated[
        str,
        BeforeValidator(strip_string),
        Field(min_length=3, max_length=254, example="johndoe_or_user@example.com"),
    ]
    password: Annotated[
        StrippedString,
        Field(min_length=8, max_length=128, example="strongpassword123"),
    ]

    @field_validator("username_or_email")
    @classmethod
    def validate_username_or_email(cls, v: str) -> str:
        if "@" in v:
            v = v.lower()
            try:
                EmailStr._validate(v)
                if len(v) > 254:
                    raise ValueError("Email address is too long.")
                return v
            except ValueError as e:
                raise ValueError(f"Invalid email format: {str(e)}")
        else:
            v = v.lower()
            if not re.fullmatch(USERNAME_REGEX, v):
                raise ValueError(
                    "Invalid username format. Must be 3-30 characters, lowercase alphanumeric, with optional single '_' or '-' separators."
                )
            if not (3 <= len(v) <= 30):
                raise ValueError("Username must be between 3 and 30 characters.")
            return v
