"""Authentication request and response schemas."""

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("full name is required")
        return cleaned

    @field_validator("password")
    @classmethod
    def bcrypt_limit(cls, value: str) -> str:
        # bcrypt ignores bytes after the 72nd; reject instead of silently truncating.
        if len(value.encode("utf-8")) > 72:
            raise ValueError("password must be at most 72 bytes")
        if value.isdigit() or value.isalpha():
            raise ValueError("password must contain letters and numbers or symbols")
        return value

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterRequest":
        if self.password != self.confirm_password:
            raise ValueError("passwords do not match")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class PublicUser(BaseModel):
    user_id: str
    full_name: str
    email: EmailStr


class CurrentUser(PublicUser):
    status: str


class RegisterData(BaseModel):
    user_id: str
    full_name: str
    email: EmailStr


class LoginData(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: PublicUser
