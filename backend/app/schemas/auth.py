"""Authentication request and response schemas."""

from pydantic import BaseModel, EmailStr, Field, model_validator


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

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
