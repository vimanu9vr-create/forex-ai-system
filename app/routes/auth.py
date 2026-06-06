from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import AUTH_PASSWORD, AUTH_TOKEN, AUTH_USERNAME

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/auth/login")
def login(payload: LoginRequest):
    if payload.username != AUTH_USERNAME or payload.password != AUTH_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return {
        "token": AUTH_TOKEN or "local-dev-token",
        "token_type": "bearer",
    }
