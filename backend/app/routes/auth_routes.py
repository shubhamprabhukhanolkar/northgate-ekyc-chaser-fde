import time
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from pydantic import BaseModel, Field
from ..auth import current_user, hasher, token_for, password_hash
from ..config import settings
from ..db import rows, connect, audit

router = APIRouter(prefix="/api/auth", tags=["auth"])
attempts = {}
dummy_hash = password_hash("not-a-user-password")


class Login(BaseModel):
    email: str = Field(max_length=200)
    password: str = Field(max_length=300)


@router.post("/login")
def login(body: Login, response: Response, request: Request):
    key = (request.client.host if request.client else "unknown", body.email.lower())
    recent = [t for t in attempts.get(key, []) if time.monotonic()-t < 300]
    attempts[key] = recent
    if len(recent) >= 10:
        raise HTTPException(429, "Too many login attempts; wait five minutes")
    found = rows("SELECT * FROM users WHERE email=?", (body.email.lower(),))
    if not hasher.verify(body.password, found[0]["password_hash"] if found else dummy_hash) or not found:
        recent.append(time.monotonic())
        raise HTTPException(401, "Invalid email or password")
    user = {k: found[0][k] for k in ("email", "name", "role")}
    token = token_for(user)
    response.set_cookie("northgate_session", token, httponly=True, secure=settings().secure_cookies, samesite="strict", max_age=8*3600)
    with connect() as db:
        audit(db, user["email"], "login")
    return {"user": user, "access_token": token, "token_type": "bearer"}


@router.get("/me")
def me(user=Depends(current_user)):
    return user


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("northgate_session")
    return {"ok": True}
