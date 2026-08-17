from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    organization_id: str = Field(min_length=3, max_length=128)
    role: str = Field(default="user", pattern="^(user|staff|manager|admin)$")
    invite_code: str | None = Field(default=None, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserResource(BaseModel):
    id: str
    name: str
    email: str
    organization_id: str
    role: str
    active: bool


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResource


class UpdateUserRequest(BaseModel):
    role: str | None = Field(default=None, pattern="^(user|staff|manager|admin)$")
    active: bool | None = None
