# app/db/schemas/user_schemas.py
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator, BeforeValidator
from typing import Optional, Annotated
from datetime import datetime
import re
import bleach  # For HTML sanitization

# --- Helper Functions for BeforeValidators ---


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

# For general strings that should be stripped of leading/trailing whitespace
StrippedString = Annotated[str, BeforeValidator(strip_string)]

# For identifiers like emails and usernames that should be lowercase and stripped
LowerStrippedString = Annotated[
    str, BeforeValidator(strip_string), BeforeValidator(string_to_lower)
]

# For full names: stripped, HTML-sanitized (text-only), and then validated with regex
SanitizedFullNameString = Annotated[
    str,
    BeforeValidator(strip_string),
    BeforeValidator(bleach_clean_text_only),  # Apply bleach before regex validation
]

# --- Regex Patterns ---
# Username: starts with lowercase alphanumeric, can have single '_' or '-' followed by more lowercase alphanumeric.
# No leading/trailing/multiple separators.
USERNAME_REGEX = r"^[a-z0-9]+(?:[_-][a-z0-9]+)*$"
# Full Name: Allows letters (including common international ones), spaces, apostrophes, hyphens.
# Must start and end with a letter. Separators must be single and surrounded by letters.
FULL_NAME_REGEX = r"^[a-zA-ZÀ-ÿ]+(?:[\s'-][a-zA-ZÀ-ÿ]+)*$"


# --- Base Schemas ---
class UserBase(BaseModel):
    email: Annotated[
        EmailStr,  # Pydantic's EmailStr handles basic email format and normalization
        BeforeValidator(strip_string),
        BeforeValidator(string_to_lower),  # Ensure emails are stored/compared in lowercase
        Field(max_length=254, example="user@example.com"),
    ]
    username: Annotated[
        LowerStrippedString,  # Handles strip and to_lower
        Field(
            min_length=3,
            max_length=30,  # Reduced for stricter control
            pattern=USERNAME_REGEX,
            example="johndoe",
        ),
    ]
    full_name: Optional[
        Annotated[
            SanitizedFullNameString,  # Handles strip and bleach
            Field(
                min_length=2,  # e.g. "Jo Do"
                max_length=100,
                pattern=FULL_NAME_REGEX,
                example="John Doe",
            ),
        ]
    ] = None


# --- Schemas for User Creation ---
class UserCreate(UserBase):
    password: Annotated[
        StrippedString,  # Strip whitespace from password input
        Field(
            min_length=12,  # Increased for better security baseline
            max_length=128,  # Reasonable upper limit
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

    class Config:
        from_attributes = True


# --- Schemas for User Update ---
class UserUpdate(BaseModel):
    # Each field mirrors the strictness of UserBase but is Optional
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
class UserLoginSchema(BaseModel):
    username_or_email: Annotated[
        str,  # Start with basic string, validators will refine
        BeforeValidator(strip_string),  # Always strip first
        Field(min_length=3, max_length=254, example="johndoe_or_user@example.com"),
    ]
    password: Annotated[
        StrippedString,
        Field(
            min_length=8, max_length=128, example="strongpassword123"
        ),  # Min length for login can be less strict than creation
    ]

    @field_validator("username_or_email")
    @classmethod
    def validate_username_or_email(cls, v: str) -> str:
        # After stripping, check if it looks like an email
        if "@" in v:
            # Attempt to validate as EmailStr (which also normalizes to lowercase by default in Pydantic v1,
            # for v2 we ensure lowercase with our BeforeValidator or by re-applying)
            # We'll re-apply lowercase here for clarity if it's an email.
            v = v.lower()
            try:
                EmailStr._validate(v)  # Use EmailStr's internal validation
                # Check max_length for email part if EmailStr doesn't enforce it strictly enough
                if (
                    len(v) > 254
                ):  # Redundant if EmailStr Field has max_length, but good for explicit check
                    raise ValueError("Email address is too long.")
                return v
            except ValueError as e:  # Catches Pydantic's validation error for EmailStr
                raise ValueError(f"Invalid email format: {str(e)}")
        else:
            # Treat as username: apply lowercase and regex
            v = v.lower()
            if not re.fullmatch(USERNAME_REGEX, v):
                raise ValueError(
                    "Invalid username format. Must be 3-30 characters, lowercase alphanumeric, with optional single '_' or '-' separators."
                )
            if not (3 <= len(v) <= 30):  # Check length for username part
                raise ValueError("Username must be between 3 and 30 characters.")
            return v
