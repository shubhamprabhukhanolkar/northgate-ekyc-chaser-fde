from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException, Request
from pwdlib import PasswordHash
from .config import settings

hasher = PasswordHash.recommended()
password_hash = hasher.hash


def token_for(user):
    return jwt.encode({"sub": user["email"], "purpose": "session", "exp": datetime.now(timezone.utc)+timedelta(hours=8)}, settings().auth_secret, algorithm="HS256")


def current_user(request: Request):
    from .db import rows
    token = request.cookies.get("northgate_session") or request.headers.get("authorization", "").removeprefix("Bearer ")
    try:
        claim = jwt.decode(token, settings().auth_secret, algorithms=["HS256"])
        if claim.get("purpose") not in (None, "session"):
            raise ValueError()
        found = rows("SELECT email,name,role FROM users WHERE email=?", (claim["sub"],))
        if not found:
            raise ValueError()
        return found[0]
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(401, "Please sign in")


def require(*roles):
    def check(user=Depends(current_user)):
        if user["role"] not in roles:
            raise HTTPException(403, "This action requires an authorized operator role")
        return user
    return check
