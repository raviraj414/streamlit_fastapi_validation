# backend/models.py
from pydantic import BaseModel
from typing import Optional

class SignupModel(BaseModel):
    name: str
    email: str
    password: str
    role: Optional[str] = "validator"

class LoginModel(BaseModel):
    email: str
    password: str

class MarkCommandModel(BaseModel):
    user_id: int
    command_id: int
    command_text: str

class UpdateLastCmdModel(BaseModel):
    user_id: int
    last_cmd_id: int
