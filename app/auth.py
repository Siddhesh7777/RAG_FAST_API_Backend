import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from app.security import create_token, decode_token, hash_password, verify_password
from app.users import get_user, visibility_for

router = APIRouter(prefix="/auth", tags=["auth"])

# Tells FastAPI the token arrives as "Authorization: Bearer <token>".
# It also gives /docs an "Authorize" button that logs in through /auth/login.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# When the username doesn't exist we still do one hash check against this dummy,
# so "no such user" takes as long as "wrong password". Otherwise response time
# would reveal which usernames exist.
_DUMMY_HASH = hash_password("dummy-password-for-timing")


def current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Use as a dependency: any endpoint that has it requires a valid token."""
    error = HTTPException(
        status_code=401,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        username = decode_token(token)
    except jwt.PyJWTError:  # bad signature, expired, garbage... all the same answer
        raise error
    user = get_user(username)  # role comes from the DATABASE, not the token
    if user is None or not user["active"]:
        raise error
    return user


def require_admin(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(
            status_code=403, detail="Admin only"
        )  # 403 = known, but not allowed
    return user


@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    user = get_user(form.username)
    stored = user["password_hash"] if user else _DUMMY_HASH
    password_ok = verify_password(form.password, stored)

    # One message for every failure, so attackers learn nothing.
    if not (user and password_ok and user["active"]):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": create_token(user["username"]), "token_type": "bearer"}


@router.get("/me")
def me(user: dict = Depends(current_user)):
    return {
        "username": user["username"],
        "role": user["role"],
        "department": user["department"],
        "visibility": visibility_for(user["role"]),
    }


@router.get("/admin-check")
def admin_check(user: dict = Depends(require_admin)):
    return {"ok": True, "admin": user["username"]}
