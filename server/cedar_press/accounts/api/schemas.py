"""Account authentication and activation request schemas."""

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


class CodeCheck(BaseModel):
    code: str
    email: str


class Activation(BaseModel):
    code: str
    email: str
    password: str
