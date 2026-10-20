from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)
    tenant_slug: str | None = None


class TenantInfo(BaseModel):
    id: UUID
    slug: str
    name: str


class UserInfo(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserInfo
    tenant: TenantInfo
    roles: list[str]


class MeResponse(BaseModel):
    user: UserInfo
    tenant: TenantInfo
    roles: list[str]


class SwitchTenantRequest(BaseModel):
    tenant_slug: str


class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)
    display_name: str = Field(min_length=1, max_length=255)
    role: Literal["admin", "legal_reviewer", "business_submitter"]


class AdminUserRead(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str
    roles: list[str]
