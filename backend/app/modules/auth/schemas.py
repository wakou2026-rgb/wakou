from typing import Literal

from pydantic import BaseModel, EmailStr


RoleLiteral = Literal["buyer", "admin", "super_admin", "sales", "maintenance"]


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    role: RoleLiteral


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str


class MeResponse(BaseModel):
    email: EmailStr
    role: RoleLiteral
    display_name: str
