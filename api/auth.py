import os
import secrets
import jwt
import bcrypt
import requests
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Header

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 30

GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")
GITHUB_CALLBACK_URL = os.environ.get("GITHUB_CALLBACK_URL", "http://localhost:8000/auth/github/callback")

# Single-process dev setup — fine for now, would need a shared store (Redis) if this ever ran multiple workers
_pending_states = set()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_access_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(authorization: str = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.removeprefix("Bearer ")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    return payload["sub"]


def build_github_authorize_url() -> str:
    state = secrets.token_urlsafe(16)
    _pending_states.add(state)
    return (
        "https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={GITHUB_CALLBACK_URL}"
        "&scope=read:user"
        f"&state={state}"
    )


def verify_state(state: str) -> bool:
    if state in _pending_states:
        _pending_states.discard(state)
        return True
    return False


def exchange_code_for_github_user(code: str) -> dict:
    token_response = requests.post(
        "https://github.com/login/oauth/access_token",
        data={
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": GITHUB_CALLBACK_URL,
        },
        headers={"Accept": "application/json"},
    )
    token_data = token_response.json()
    if "error" in token_data:
        raise HTTPException(status_code=400, detail=token_data.get("error_description", "GitHub token exchange failed"))

    access_token = token_data["access_token"]

    user_response = requests.get(
        "https://api.github.com/user",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
        },
    )
    return user_response.json()
