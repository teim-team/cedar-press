"""Account authentication and setup request schemas."""

from pydantic import BaseModel, Field


class Credentials(BaseModel):
    email: str
    password: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class ResetRequest(BaseModel):
    email: str = Field(max_length=254)
    next: str = Field(default="/", max_length=2048)


class ResetConfirm(BaseModel):
    token: str = Field(max_length=128)
    new_password: str


class AccountLink(BaseModel):
    token: str = Field(max_length=128)


class AccountSetup(ResetConfirm):
    name: str = Field(min_length=1, max_length=120)


class ProfileChange(BaseModel):
    name: str | None = Field(default=None, max_length=120)

