import hashlib
import os
from jose import jwt, JWTError
from datetime import datetime, timedelta
from fastapi import HTTPException, Security, Depends
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
import database

SECRET_KEY = os.getenv("JWT_SECRET", "super-secret-directorate-key-for-gdc-management-system-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440 # 24 hours

api_key_header = APIKeyHeader(name="X-College-API-Key", auto_error=False)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Format of hashed_password: "salt:sha256"
    if ":" not in hashed_password:
        return False
    salt, val = hashed_password.split(":", 1)
    calc = hashlib.sha256((salt + plain_password).encode("utf-8")).hexdigest()
    return calc == val

def get_password_hash(password: str) -> str:
    salt = os.urandom(8).hex()
    calc = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}:{calc}"


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_api_key(college_id: str, api_key: str) -> bool:
    if not college_id or not api_key:
        return False
    with database.get_db() as conn:
        row = conn.execute("SELECT api_key FROM colleges WHERE id = ?", (college_id,)).fetchone()
        if row and row["api_key"] == api_key:
            return True
    return False

def get_current_user(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"email": email, "role": payload.get("role", "directorate_admin")}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
